from flask import Flask, request, jsonify, send_from_directory
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import sqlite3
import json
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download VADER lexicon
nltk.download('vader_lexicon')

app = Flask(__name__)

# Ensure static folder exists
if not os.path.exists('static'):
    os.makedirs('static')

# Hugging Face API configuration
API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment"
HUGGINGFACE_TOKEN = "your_api_key_here"
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

# Initialize VADER sentiment analyzer
sid = SentimentIntensityAnalyzer()

# Initialize SQLite database


def init_db():
    conn = sqlite3.connect('sentiment_analysis.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analyses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  text TEXT NOT NULL,
                  sentiment TEXT NOT NULL,
                  score REAL NOT NULL,
                  positive_score REAL NOT NULL,
                  word_sentiments TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  analysis_count INTEGER DEFAULT 0,
                  positive_count INTEGER DEFAULT 0,
                  negative_count INTEGER DEFAULT 0,
                  neutral_count INTEGER DEFAULT 0,
                  date DATE UNIQUE)''')
    conn.commit()
    conn.close()


init_db()


def query(payload):
    """Send payload to Hugging Face API and return response."""
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        # Query Hugging Face API for overall sentiment
        output = query({"inputs": text})
        if not output or isinstance(output, dict) and 'error' in output:
            return jsonify({'error': 'API request failed'}), 500

        # Process API output
        scores = {item['label']: item['score'] for item in output[0]}
        sentiment_map = {'LABEL_0': 'negative',
                         'LABEL_1': 'neutral', 'LABEL_2': 'positive'}
        max_label = max(scores, key=scores.get)
        sentiment = sentiment_map[max_label]
        confidence = scores[max_label]
        positive_score = scores.get('LABEL_2', 0)

        # Get word-level sentiments using VADER
        words = text.split()
        word_sentiments = [
            {'text': word, 'sentiment': 'positive' if (score := sid.polarity_scores(
                word)['compound']) > 0 else 'negative' if score < 0 else 'neutral', 'score': abs(score)}
            for word in words if len(word) > 2
        ]

        # Store analysis in database
        conn = sqlite3.connect('sentiment_analysis.db')
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO analyses (text, sentiment, score, positive_score, word_sentiments)
                         VALUES (?, ?, ?, ?, ?)''',
                      (text, sentiment, confidence, positive_score, json.dumps(word_sentiments)))

            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('''INSERT INTO analytics 
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
                       1 if sentiment == 'neutral' else 0))

            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            return jsonify({'error': 'Database error occurred'}), 500
        finally:
            conn.close()

        return jsonify({
            'sentiment': sentiment,
            'score': confidence,
            'positive_score': positive_score,
            'word_sentiments': word_sentiments
        })

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({'error': 'An error occurred during analysis'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    try:
        conn = sqlite3.connect('sentiment_analysis.db')
        c = conn.cursor()

        c.execute('''SELECT 
                        COUNT(*) as total, 
                        SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive,
                        SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative,
                        SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral
                     FROM analyses''')
        counts = c.fetchone()

        c.execute('''SELECT text, sentiment, score, timestamp 
                     FROM analyses ORDER BY id DESC LIMIT 5''')
        recent = [
            {'text': r[0][:100] + '...' if len(r[0]) > 100 else r[0],
             'sentiment': r[1], 'score': r[2], 'timestamp': r[3]}
            for r in c.fetchall()
        ]

        conn.close()

        return jsonify({
            'total': counts[0] or 0,
            'positive': counts[1] or 0,
            'negative': counts[2] or 0,
            'neutral': counts[3] or 0,
            'recent': recent
        })

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'An error occurred while fetching statistics'}), 500


if __name__ == '__main__':
    app.run(debug=True)
