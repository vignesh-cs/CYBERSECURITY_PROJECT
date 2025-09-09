import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
from sklearn.model_selection import train_test_split

# Sample training data
training_data = [
    ("ransomware encryption files using SMBv1 vulnerability", "DISABLE_SMBv1", "CRITICAL"),
    ("phishing email attempting credential theft", "ENABLE_MFA", "HIGH"),
    ("exploit targeting remote desktop protocol port 3389", "BLOCK_RDP_PORT", "CRITICAL"),
    ("unauthorized access attempt from external IP", "QUARANTINE_ENDPOINT", "HIGH"),
    ("data exfiltration over network shares", "ENABLE_DLP", "HIGH"),
    ("ddos attack targeting network infrastructure", "RATE_LIMIT_TRAFFIC", "HIGH"),
    ("malware execution detected on endpoint", "ISOLATE_ENDPOINT", "CRITICAL"),
    ("sql injection attempt on web application", "WAF_UPDATE", "MEDIUM"),
    ("brute force attack on user accounts", "LOCK_ACCOUNTS", "HIGH"),
    ("suspicious PowerShell execution", "RESTRICT_PS", "MEDIUM"),
    ("weak password policy detected", "PASSWORD_POLICY", "MEDIUM"),
    ("unencrypted data transmission", "ENABLE_ENCRYPTION", "HIGH"),
    ("missing security patches", "APPLY_PATCHES", "HIGH"),
    ("excessive user privileges", "REVIEW_PERMISSIONS", "MEDIUM"),
    ("open network ports", "CLOSE_PORTS", "MEDIUM"),
    ("disabled antivirus", "ENABLE_ANTIVIRUS", "HIGH"),
    ("disabled firewall", "ENABLE_FIREWALL", "HIGH"),
    ("outdated software version", "UPDATE_SOFTWARE", "MEDIUM"),
    ("suspicious network traffic", "INVESTIGATE_TRAFFIC", "HIGH"),
    ("unauthorized software installation", "REMOVE_SOFTWARE", "MEDIUM")
]

# Create DataFrame
df = pd.DataFrame(training_data, columns=['threat_description', 'required_action', 'severity'])

# Create pipeline
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.8
    )),
    ('clf', RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    ))
])

# Train the model
X = df['threat_description']
y = df['required_action']  # You can also use 'severity' for different models

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training threat classification model...")
pipeline.fit(X_train, y_train)

# Evaluate the model
accuracy = pipeline.score(X_test, y_test)
print(f"Model accuracy: {accuracy:.2f}")

# Save the model
model_path = '/app/models/threat_classifier_model.pkl'
joblib.dump(pipeline, model_path)
print(f"Model saved to: {model_path}")

# Create a sample model for testing
sample_model = {
    'model_type': 'RandomForestClassifier',
    'version': '1.0',
    'training_date': pd.Timestamp.now().isoformat(),
    'accuracy': accuracy,
    'features': 1000,
    'classes': list(y.unique()),
    'pipeline': pipeline
}

joblib.dump(sample_model, '/app/models/sample_model.pkl')
print("Sample model created for testing")