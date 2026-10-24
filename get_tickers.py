import pandas as pd

# Load your preprocessed data
df = pd.read_csv('data/ohlcv_data.csv')

# Get the unique list of stocks that passed the <20% missing data filter
valid_stocks = sorted(df['Ticker'].unique().tolist())

print(f"Total stocks that passed preprocessing: {len(valid_stocks)}\n")
print("Here is the exact list:")
print(", ".join(valid_stocks))

# Optional: Save this list to a text file for your report
with open('valid_stocks_list.txt', 'w') as f:
    f.write("\n".join(valid_stocks))
print("\n✅ List saved to 'valid_stocks_list.txt'")