# Voice Module - AI-Powered Transaction Parser

Natural language transaction parsing and AI-powered categorization using voice or text input.

## Features

- **Voice Input**: Speak transactions naturally
- **Text Parsing**: Type transactions in plain English/Hinglish
- **AI Categorization**: Uses Groq's Llama 3.3-70B model for intelligent categorization
- **Rule-Based Fallback**: Category rules for common keywords
- **Category Corrections**: Learn from user corrections and apply to future transactions
- **Multi-Transaction Support**: Extract multiple transactions from a single input
- **Financial Summaries**: Revenue, expenses, and profit tracking

## Architecture

```
voice-module/
├── server.py           # Flask REST API server
├── parser.py           # AI-powered transaction parser (Groq Llama 3.3)
├── categorizer.py      # Rule-based + AI categorization
├── index.html          # Frontend UI with voice input
├── tests/              # Unit tests
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Endpoints

### POST /parse

Parse natural language text into structured transactions.

**Request:**

```json
{
  "text": "bought flour for 200 and sold cakes for 500"
}
```

**Response:**

```json
{
  "success": true,
  "parsed": [
    {
      "description": "flour",
      "amount": 200,
      "type": "expense",
      "category": "Inventory",
      "date": "2026-03-05",
      "confidence_score": 0.85
    },
    {
      "description": "sold cakes",
      "amount": 500,
      "type": "income",
      "category": "Revenue",
      "date": "2026-03-05",
      "confidence_score": 0.9
    }
  ],
  "count": 2
}
```

### POST /categorize

Apply AI categorization to transactions.

**Request:**

```json
{
  "transactions": [{ "description": "office rent", "amount": 5000 }]
}
```

### POST /save-transactions

Save categorized transactions to Supabase.

### POST /correct-category

Correct a transaction's category and save as override rule.

### GET /transactions

Retrieve transactions with optional filters (category, type, limit).

### GET /summary

Get financial summary (revenue, expenses, profit).

### GET /categories/summary

Get spending breakdown by category.

### GET /health

Health check endpoint.

## Setup

### Prerequisites

- Python 3.11+
- Groq API Key (get from [console.groq.com](https://console.groq.com))
- Supabase project (URL and Key)

### Installation

```bash
cd voice-module

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Add to ../../.env:
# GROQ_API_KEY=your_groq_api_key_here
```

### Running the Server

```bash
# Development mode (auto-reload)
python server.py

# Or with custom port
PORT=5000 python server.py
```

Server will start on `http://localhost:5000`

### Running Tests

```bash
pytest tests/
```

## Usage Examples

### Parse Transaction

```bash
curl -X POST http://localhost:5000/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "paid 3000 for electricity bill"}'
```

### Get Summary

```bash
curl http://localhost:5000/summary
```

### Frontend UI

Open `index.html` in a browser or serve via Flask to use the voice input interface.

## Categories

- **Revenue**: Sales, income, payments received
- **Inventory**: Stock purchases, raw materials
- **Utilities**: Electricity, internet, phone bills
- **Rent**: Shop/office rent payments
- **Salaries**: Employee wages, staff payments
- **Transport**: Fuel, delivery charges, travel
- **Marketing**: Ads, promotions, banners
- **Maintenance**: Repairs, cleaning, services
- **Personal**: Personal expenses (flagged separately)
- **Food**: Meals, restaurant bills
- **Other**: Miscellaneous

## Integration with Backend

The voice module can be used standalone or integrated with the main FastAPI backend:

1. Parse transactions using `/parse`
2. Optionally categorize using `/categorize`
3. Save to backend API at `http://127.0.0.1:8000/transactions`

## Configuration

Environment variables (set in `../../.env`):

- `GROQ_API_KEY`: Groq API key for AI parsing
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/service key
- `PORT`: Server port (default: 5000)

## Technology Stack

- **Flask**: Web framework
- **Groq API**: AI model (Llama 3.3-70B)
- **Supabase**: PostgreSQL database
- **pytest**: Testing framework
- **Flask-CORS**: Cross-origin resource sharing

## Docker Support

See `../docker-compose.yml` for containerized deployment.

## Development

### Adding New Categories

Edit `CATEGORY_RULES` in `categorizer.py`:

```python
CATEGORY_RULES = {
    "NewCategory": ["keyword1", "keyword2", ...]
}
```

### Improving Parser

Update prompt in `parser.py` to add new parsing rules or improve accuracy.

## Troubleshooting

**Issue**: "GROQ_API_KEY not found"

- **Solution**: Set `GROQ_API_KEY` in `.env` file

**Issue**: Connection to Supabase fails

- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct

**Issue**: Categories not accurate

- **Solution**: Use `/correct-category` endpoint to train the system

## License

Part of the pocketCFO project.
