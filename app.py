from flask import Flask, request, jsonify, send_from_directory
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import sqlite3
import json
from datetime import datetime
import os
import logging
import gc
import re
from functools import wraps
import time
from threading import Lock
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download VADER lexicon
nltk.download('vader_lexicon', quiet=True)

app = Flask(__name__)

# Ensure static folder exists
if not os.path.exists('static'):
    os.makedirs('static')

# Singleton pattern for model management


class ModelManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelManager, cls).__new__(cls)
                cls._instance.sentiment_analyzer = None
                cls._instance.sid = None
                cls._instance.tokenizer = None  # Add tokenizer
                cls._instance.initialized = False
            return cls._instance

    def initialize(self):
        if not self.initialized:
            logger.info("Loading sentiment analysis models...")
            model_name = "cardiffnlp/twitter-roberta-base-sentiment"

            logger.info("Falling back to standard PyTorch model")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name)  # Store tokenizer
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name)
            self.sentiment_analyzer = pipeline(
                "text-classification",
                model=model,
                tokenizer=self.tokenizer
            )
            logger.info("Using standard PyTorch model")

            self.sid = SentimentIntensityAnalyzer()
            self.initialized = True
            logger.info("Models loaded successfully")

    def get_sentiment_analyzer(self):
        self.initialize()
        return self.sentiment_analyzer

    def get_vader_analyzer(self):
        self.initialize()
        return self.sid

    def get_tokenizer(self):
        self.initialize()
        return self.tokenizer

    def cleanup(self):
        if self.initialized:
            del self.sentiment_analyzer
            del self.sid
            del self.tokenizer
            self.sentiment_analyzer = None
            self.sid = None
            self.tokenizer = None
            self.initialized = False
            gc.collect()
            logger.info("Model resources released")




class DatabaseManager:
    DB_PATH = 'sentiment_analysis.db'
    _connection_pool = {}
    _lock = Lock()

    @classmethod
    @contextmanager
    def get_connection(cls):
        with cls._lock:
            conn = sqlite3.connect(cls.DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    @classmethod
    def init_db(cls):
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS analyses
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         text TEXT NOT NULL,
                         sentiment TEXT NOT NULL,
                         score REAL NOT NULL,
                         positive_score REAL NOT NULL,
                         word_sentiments TEXT NOT NULL,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS analytics
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         analysis_count INTEGER DEFAULT 0,
                         positive_count INTEGER DEFAULT 0,
                         negative_count INTEGER DEFAULT 0,
                         neutral_count INTEGER DEFAULT 0,
                         date DATE UNIQUE)''')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_analyses_sentiment ON analyses(sentiment)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(date)')
            conn.commit()

    @classmethod
    def store_analysis(cls, text, sentiment, confidence, positive_score, word_sentiments):
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    '''INSERT INTO analyses (text, sentiment, score, positive_score, word_sentiments)
                    VALUES (?, ?, ?, ?, ?)''',
                    (text, sentiment, confidence,
                     positive_score, json.dumps(word_sentiments))
                )
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    '''INSERT INTO analytics
                    (date, analysis_count, positive_count, negative_count, neutral_count)
                    VALUES (?, 1, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                    analysis_count = analysis_count + 1,
                    positive_count = positive_count + ?,
                    negative_count = negative_count + ?,
                    neutral_count = neutral_count + ?''',
                    (today,
                     1 if sentiment == 'positive' else 0,
                     1 if sentiment == 'negative' else 0,
                     1 if sentiment == 'neutral' else 0,
                     1 if sentiment == 'positive' else 0,
                     1 if sentiment == 'negative' else 0,
                     1 if sentiment == 'neutral' else 0)
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}")
                conn.rollback()
                return False

    @classmethod
    def get_stats(cls):
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT
                       COUNT(*) as total,
                       SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative,
                       SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral
                       FROM analyses''')
            counts = cursor.fetchone()
            cursor.execute('''SELECT text, sentiment, score, timestamp
                       FROM analyses ORDER BY id DESC LIMIT 5''')
            recent = [
                {
                    'text': row['text'][:100] + '...' if len(row['text']) > 100 else row['text'],
                    'sentiment': row['sentiment'],
                    'score': row['score'],
                    'timestamp': row['timestamp']
                }
                for row in cursor.fetchall()
            ]
            return {
                'total': counts['total'] or 0,
                'positive': counts['positive'] or 0,
                'negative': counts['negative'] or 0,
                'neutral': counts['neutral'] or 0,
                'recent': recent
            }


# Initialize the database
DatabaseManager.init_db()
model_manager = ModelManager()

# Decorators


def sanitize_input(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if request.is_json:
            data = request.get_json(force=True, silent=True) or {}
            if 'text' in data and isinstance(data['text'], str):
                data['text'] = re.sub(r'[^\w\s.,!?\'"-]', '', data['text'])
            if 'texts' in data and isinstance(data['texts'], list):
                data['texts'] = [
                    re.sub(r'[^\w\s.,!?\'"-]', '',
                           text) if isinstance(text, str) else ""
                    for text in data['texts']
                ]
            request.data = json.dumps(data).encode('utf-8')
        return func(*args, **kwargs)
    return wrapped


request_history = {}
RATE_LIMIT = 10
TIME_WINDOW = 60


def rate_limit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        request_history[client_ip] = [
            timestamp for timestamp in request_history.get(client_ip, [])
            if timestamp > current_time - TIME_WINDOW
        ]
        if len(request_history.get(client_ip, [])) >= RATE_LIMIT:
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        if client_ip not in request_history:
            request_history[client_ip] = []
        request_history[client_ip].append(current_time)
        return func(*args, **kwargs)
    return wrapped

# Routes


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/analyze', methods=['POST'])
@sanitize_input
@rate_limit
def analyze():
    data = request.json
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        sentiment_analyzer = model_manager.get_sentiment_analyzer()
        sid = model_manager.get_vader_analyzer()
        tokenizer = model_manager.get_tokenizer()  # Get tokenizer

        # Truncate text to 512 tokens
        tokens = tokenizer.encode(text, add_special_tokens=True)
        if len(tokens) > 512:
            tokens = tokens[:510] + tokens[-2:]
            text = tokenizer.decode(tokens, skip_special_tokens=True)

        result = sentiment_analyzer(text)[0]
        logger.info(f"Result type: {type(result)}, content: {result}")

        sentiment_map = {'LABEL_0': 'negative',
                         'LABEL_1': 'neutral', 'LABEL_2': 'positive'}
        sentiment = sentiment_map[result['label']]
        confidence = result['score']

        all_scores = sentiment_analyzer(text, top_k=None)[0]
        logger.info(
            f"All scores type: {type(all_scores)}, content: {all_scores}")
        if isinstance(all_scores, dict):
            scores = {all_scores['label']: all_scores['score']}
        else:
            scores = {item['label']: item['score'] for item in all_scores}
        positive_score = scores.get('LABEL_2', 0)

        words = text.split()
        word_sentiments = []
        if len(words) < 500:
            word_sentiments = [
                {
                    'text': word,
                    'sentiment': 'positive' if (score := sid.polarity_scores(word)['compound']) > 0
                    else 'negative' if score < 0 else 'neutral',
                    'score': abs(score)
                }
                for word in words if len(word) > 2
            ]

        success = DatabaseManager.store_analysis(
            text, sentiment, confidence, positive_score, word_sentiments
        )
        if not success:
            return jsonify({'error': 'Database error occurred'}), 500

        return jsonify({
            'sentiment': sentiment,
            'score': confidence,
            'positive_score': positive_score,
            'word_sentiments': word_sentiments
        })

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'error': 'An error occurred during analysis'}), 500


@app.route('/stats', methods=['GET'])
@rate_limit
def get_stats():
    try:
        stats = DatabaseManager.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching statistics'}), 500


@app.route('/memory-cleanup', methods=['POST'])
def memory_cleanup():
    try:
        model_manager.cleanup()
        collected = gc.collect()
        return jsonify({
            'success': True,
            'collected_objects': collected
        })
    except Exception as e:
        logger.error(f"Memory cleanup error: {str(e)}")
        return jsonify({'error': 'Memory cleanup failed'}), 500


@app.route('/analyze-batch', methods=['POST'])
@sanitize_input
@rate_limit
def analyze_batch():
    data = request.json
    texts = data.get('texts', [])
    if not texts:
        return jsonify({'error': 'No texts provided'}), 400
    if len(texts) > 50:
        return jsonify({'error': 'Batch size too large. Maximum 50 texts per request.'}), 400
    try:
        sentiment_analyzer = model_manager.get_sentiment_analyzer()
        results = sentiment_analyzer(texts, top_k=None)
        processed_results = []
        for i, result_scores in enumerate(results):
            max_score = max(result_scores, key=lambda x: x['score'])
            sentiment_map = {'LABEL_0': 'negative',
                             'LABEL_1': 'neutral', 'LABEL_2': 'positive'}
            sentiment = sentiment_map[max_score['label']]
            confidence = max_score['score']
            positive_score = next(
                (item['score'] for item in result_scores if item['label'] == 'LABEL_2'), 0)
            processed_results.append({
                'text': texts[i],
                'sentiment': sentiment,
                'score': confidence,
                'positive_score': positive_score
            })
        return jsonify({'results': processed_results})
    except Exception as e:
        logger.error(f"Batch analysis error: {str(e)}")
        return jsonify({'error': 'An error occurred during batch analysis'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
