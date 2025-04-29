# SentiViz: Sentiment Analysis Dashboard

SentiViz is an interactive web-based dashboard designed for sentiment analysis, utilizing advanced natural language processing (NLP) techniques to evaluate the emotional tone of text. This project combines deep learning and rule-based methods to deliver real-time insights, enhanced by engaging visualizations, making it a powerful tool for understanding sentiment in textual data.

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Usage](#usage)
  - [Text Length Considerations](#text-length-considerations)
  - [Using the Hugging Face API Version](#using-the-hugging-face-api-version)
- [Contributions](#contributions)
- [Additional Information](#additional-information)

## Introduction
SentiViz leverages two robust NLP technologies:
- **RoBERTa Model**: A transformer-based deep learning model fine-tuned on Twitter data. It excels at understanding context and nuances in text, providing accurate overall sentiment classification (positive, negative, or neutral).
- **VADER (Valence Aware Dictionary and sEntiment Reasoner)**: A rule-based model designed specifically for social media text. It uses a sentiment lexicon and grammatical rules to assess the sentiment intensity of individual words and phrases, offering detailed word-level insights.

Together, RoBERTa determines the overall sentiment of the input text, while VADER provides a granular breakdown of sentiment at the word level, enabling a comprehensive analysis of emotional tone.

### Key Features
- Real-time sentiment analysis of user-input text.
- Word-level sentiment breakdown for granular insights.
- Interactive visualizations, including a sentiment meter, emotion pie chart, and word cloud.
- Theme toggle between light and dark modes.
- History tracking to observe sentiment trends over time.

## Installation
Follow these steps to set up SentiViz on your local machine:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/NTRajapaksha/SentiViz.git
   cd sentiviz
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download NLTK Data**:
   Run the following Python commands to download the required NLTK data:
   ```python
   import nltk
   nltk.download('vader_lexicon')
   ```

5. **Run the Application**:
   - For the local version (requires computational resources):
     ```bash
     python app.py
     ```
   - For the API version (if you lack local resources, see [Using the Hugging Face API Version](#using-the-hugging-face-api-version)):
     ```bash
     python app_api.py
     ```

6. **Access the Dashboard**:
   Open your web browser and go to `http://localhost:5000`.

## Usage
Once the application is running, you can interact with SentiViz as follows:
- **Analyze Text**: Input text into the provided box and click "Analyze Sentiment" to see results instantly.
- **Live Analysis**: Enable "Live Analysis" for immediate sentiment feedback as you type.
- **Explore Visualizations**: Check the sentiment meter, emotion pie chart, and word cloud for a comprehensive view of the sentiment.
- **Switch Themes**: Use the theme toggle to switch between light and dark modes.
- **View History**: Navigate to the "History" and "Dashboard" tabs to review past analyses and trends.

### Text Length Considerations
The sentiment analysis is powered by the RoBERTa model, which has a maximum input limit of 512 tokens (approximately 400-500 words). For texts exceeding this limit, the application will truncate the input and analyze only the first 512 tokens. To ensure a complete analysis of longer texts, we recommend breaking them into smaller sections and analyzing each part separately.

### Using the Hugging Face API Version
For users who do not have the computational resources to run the sentiment analysis model locally, we provide an alternative version of the application (`app_api.py`) that utilizes the Hugging Face API. This allows you to perform sentiment analysis without needing significant local processing power.

#### Steps to Use the API Version:
1. **Obtain an API Key**:
   - Sign up for a Hugging Face account at [Hugging Face](https://huggingface.co/).
   - Generate an API key from your account settings.

2. **Set Up the API Key**:
   - Open `app_api.py` and replace the placeholder with your actual API key:
     ```python
     HUGGINGFACE_TOKEN = "your_api_key_here"
     ```

3. **Run the Application**:
   - Ensure you have an active internet connection.
   - Start the API version:
     ```bash
     python app_api.py
     ```
   - Access the dashboard at `http://localhost:5000`.

#### Important Notes:
- The API version requires an internet connection and is subject to Hugging Face's API rate limits.
- For offline use or unrestricted access, consider using the local version if resources permit.

#### Resources:
- [Hugging Face API Documentation](https://huggingface.co/docs/api-inference/index)
- [Obtaining an API Key](https://huggingface.co/docs/hub/security-tokens)

## Contributions
This project was a collaborative effort by two team members as part of a group assignment. Below are their specific contributions:

### Team Member 1: [Thathsara Rajapaksha]
- **Role**: Backend & Data Management
- **Contributions**:
  - Developed the Flask backend (`app.py`), handling routes for sentiment analysis, batch processing, and statistics.
  - Integrated RoBERTa and VADER models, including text truncation for lengthy inputs.
  - Designed and implemented the SQLite database (`DatabaseManager`) for storing analysis results.
  - Managed project dependencies in `requirements.txt`.
- **Files**: `app.py`, `requirements.txt`

### Team Member 2: [Umindu Nimsara]
- **Role**: Frontend & Visualizations
- **Contributions**:
  - Created the user interface (`index.html`) with Bootstrap and custom CSS for responsiveness.
  - Styled the dashboard with light and dark mode support (`styles.css`).
  - Implemented client-side logic (`script.js`), including real-time analysis, Plotly visualizations, and tab navigation.
  - Connected the frontend to the backend using the fetch API.
- **Files**: `index.html`, `styles.css`, `script.js`

## Additional Information
- **Troubleshooting**:
  - If you see a "tokenizer not defined" error, verify that the `ModelManager` is properly initialized.
  - For visualization issues, check the browser console for JavaScript errors.
- **Future Improvements**:
  - Add multi-language support for broader sentiment analysis.
  - Introduce user authentication for personalized dashboards.
  - Enhance visualizations with additional interactive features.
