# securebert_train.py
# Train/fine-tune SecureBERT. Saves to ai-engine/app/models/securebert/
import os
import numpy as np
import pandas as pd
from datasets import Dataset, DatasetDict
from evaluate import load as load_metric
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    EarlyStoppingCallback,
    DataCollatorWithPadding
)
from huggingface_hub import login

# Authenticate with Hugging Face using your token
HF_TOKEN = os.getenv("HF_TOKEN")
try:
    login(token=HF_TOKEN)
    print("Successfully authenticated with Hugging Face Hub")
except Exception as e:
    print(f"Authentication failed: {e}")
    print("Trying to continue without authentication...")

# Use the actual SecureBERT model
MODEL_NAME = "AliOsm/SecureBERT"
OUT_DIR = os.path.join(os.path.dirname(__file__), "models", "securebert")
os.makedirs(OUT_DIR, exist_ok=True)

# Load dataset with proper error handling
def load_dataset_safely():
    try:
        # Load CSV files with proper encoding and handling
        train_df = pd.read_csv("train.csv")
        val_df = pd.read_csv("val.csv")
        
        print(f"Train CSV shape: {train_df.shape}")
        print(f"Validation CSV shape: {val_df.shape}")
        print(f"Train columns: {train_df.columns.tolist()}")
        
        # Convert to Hugging Face dataset format
        train_dataset = Dataset.from_pandas(train_df)
        val_dataset = Dataset.from_pandas(val_df)
        
        return DatasetDict({
            "train": train_dataset,
            "validation": val_dataset
        })
        
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        print("Creating dummy dataset for testing...")
        
        # Create dummy data with proper structure
        dummy_texts = [
            "Security alert: suspicious activity detected",
            "Normal system update completed successfully",
            "Critical vulnerability found in network",
            "Routine maintenance performed without issues"
        ]
        dummy_labels = [1, 0, 1, 0]
        
        dummy_data = {
            "text": dummy_texts * 6,  # Repeat to get more samples
            "label": dummy_labels * 6
        }
        
        dummy_df = pd.DataFrame(dummy_data)
        dummy_dataset = Dataset.from_pandas(dummy_df)
        
        return DatasetDict({
            "train": dummy_dataset,
            "validation": dummy_dataset
        })

print("Loading dataset...")
ds = load_dataset_safely()
print("Dataset loaded successfully")

# Load tokenizer and model
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=2,
        token=HF_TOKEN
    )
    print("SecureBERT model and tokenizer loaded successfully")
except Exception as e:
    print(f"Error loading SecureBERT: {e}")
    print("Falling back to standard BERT model...")
    MODEL_NAME = "bert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=2
    )

# Set padding token if not set
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Preprocessing function - FIXED: Ensure proper tensor output
def preprocess(batch):
    # Extract text and ensure it's properly formatted
    texts = batch["text"]
    
    # Tokenize with proper settings
    encoding = tokenizer(
        texts, 
        truncation=True, 
        padding=False,  # We'll let the data collator handle padding
        max_length=256,
        return_tensors=None  # Don't return tensors yet
    )
    
    # Add labels to the encoding
    encoding["labels"] = batch["label"]
    
    return encoding

# Tokenize the dataset
print("Tokenizing dataset...")
try:
    ds = ds.map(preprocess, batched=True)
    print("Tokenization completed successfully")
    
    # Remove the original columns to avoid conflicts
    ds = ds.remove_columns(["text", "label"])
    
except Exception as e:
    print(f"Error during tokenization: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Compute metrics function
def compute_metrics(eval_pred):
    try:
        metric = load_metric("accuracy")
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)
    except Exception as e:
        print(f"Error loading metric: {e}")
        # Fallback calculation
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        accuracy = (predictions == labels).mean()
        return {"accuracy": accuracy}

# Create data collator for dynamic padding
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# Training arguments
training_args = TrainingArguments(
    output_dir=OUT_DIR,
    eval_strategy="epoch",
    save_strategy="epoch",
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    num_train_epochs=3,
    learning_rate=2e-5,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    greater_is_better=True,
    logging_dir='./logs',
    logging_steps=5,
    report_to="none",
    remove_unused_columns=False,
)

# Initialize Trainer with data collator
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds["train"],
    eval_dataset=ds["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,  # Add data collator for proper padding
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
)

# Train and save
print("Starting training...")
try:
    # Test a single batch first to ensure everything works
    print("Testing with one batch...")
    test_batch = next(iter(trainer.get_train_dataloader()))
    print("Batch test successful!")
    
    # Start full training
    trainer.train()
    
    # Save the model
    trainer.save_model(OUT_DIR)
    tokenizer.save_pretrained(OUT_DIR)
    
    print(f"Model saved to {OUT_DIR}")
    print("Training completed successfully!")
    
except Exception as e:
    print(f"Training failed: {e}")
    print("Detailed error information:")
    import traceback
    traceback.print_exc()
    
    # Additional debugging info
    print("\nDebugging info:")
    print(f"Dataset features: {ds['train'].features}")
    print(f"Sample item keys: {list(ds['train'][0].keys())}")
    print(f"Sample input_ids type: {type(ds['train'][0]['input_ids'])}")
    print(f"Sample input_ids value: {ds['train'][0]['input_ids'][:5]}")  # First 5 tokens