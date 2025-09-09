# rf_train.py
import os
import pickle
import pandas as pd
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

BASE = os.path.dirname(__file__)
SECUREBERT_DIR = os.path.join(BASE, "models", "securebert")
RF_OUT = os.path.join(BASE, "models", "rf_model.pkl")
RF_DATASET_PATH = os.path.join(BASE, "rf_dataset.csv")

# Create models directory if it doesn't exist
os.makedirs(os.path.dirname(RF_OUT), exist_ok=True)

# Check if SecureBERT model exists
if not os.path.exists(SECUREBERT_DIR):
    print(f"Error: SecureBERT model not found at {SECUREBERT_DIR}")
    print("Please run securebert_train.py first to train the model")
    exit(1)

# Load tokenizer and model
try:
    tokenizer = AutoTokenizer.from_pretrained(SECUREBERT_DIR)
    model = AutoModel.from_pretrained(SECUREBERT_DIR)
    model.eval()
    print("SecureBERT model loaded successfully")
except Exception as e:
    print(f"Error loading SecureBERT model: {e}")
    exit(1)

def embed_texts(texts):
    """Embed texts using SecureBERT model"""
    embs = []
    for t in texts:
        try:
            tokens = tokenizer(
                t, 
                truncation=True, 
                padding='max_length', 
                max_length=256, 
                return_tensors='pt'
            )
            with torch.no_grad():
                out = model(**tokens)
                cls = out.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
            embs.append(cls)
        except Exception as e:
            print(f"Error embedding text: '{t[:50]}...' - {e}")
            # Add zero vector as fallback
            embs.append(np.zeros(model.config.hidden_size))
    return np.vstack(embs)

# Load dataset with error handling
try:
    df = pd.read_csv(RF_DATASET_PATH)
    print(f"Dataset loaded: {df.shape[0]} samples")
    print(f"Columns: {df.columns.tolist()}")
    
    # Check if required columns exist
    if 'text' not in df.columns or 'label' not in df.columns:
        print("Error: CSV must contain 'text' and 'label' columns")
        print("Available columns:", df.columns.tolist())
        exit(1)
        
    # Check for missing values
    print(f"Missing values in text: {df['text'].isnull().sum()}")
    print(f"Missing values in label: {df['label'].isnull().sum()}")
    
    # Remove rows with missing values
    df = df.dropna(subset=['text', 'label'])
    print(f"After cleaning: {df.shape[0]} samples")
    
except FileNotFoundError:
    print(f"Error: rf_dataset.csv not found at {RF_DATASET_PATH}")
    print("Please create a CSV file with 'text' and 'label' columns")
    print("Example format:")
    print("text,label")
    print("\"Malicious phishing attempt detected\",1")
    print("\"Normal system update\",0")
    exit(1)
except Exception as e:
    print(f"Error loading dataset: {e}")
    exit(1)

# Generate embeddings
print("Generating embeddings...")
X = embed_texts(df['text'].tolist())
y = df['label'].tolist()

print(f"Embeddings shape: {X.shape}")
print(f"Labels: {len(y)}")

# Split data
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training samples: {len(X_train)}")
print(f"Validation samples: {len(X_val)}")

# Train Random Forest classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42, verbose=1)
print("Training Random Forest classifier...")
clf.fit(X_train, y_train)

# Evaluate
pred = clf.predict(X_val)
accuracy = accuracy_score(y_val, pred)
print("RF validation accuracy:", accuracy)

# Detailed classification report
print("\nClassification Report:")
print(classification_report(y_val, pred))

# Save model
try:
    with open(RF_OUT, "wb") as f:
        pickle.dump(clf, f)
    print(f"Saved RF model to {RF_OUT}")
except Exception as e:
    print(f"Error saving model: {e}")

# Optional: Test with sample predictions
print("\nSample predictions:")
sample_texts = [
    "Security alert: malware detected in system",
    "Regular system maintenance completed",
    "Unauthorized access attempt blocked"
]

sample_embeddings = embed_texts(sample_texts)
sample_preds = clf.predict(sample_embeddings)

for text, pred in zip(sample_texts, sample_preds):
    print(f"'{text[:50]}...' -> Prediction: {pred}")