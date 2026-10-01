import os
import base64
import binascii
import json
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from categorizer import apply_categorization

from supabase import create_client
app = Flask(__name__)
CORS(app, origins=os.getenv("VOICE_CORS_ORIGIN", "http://127.0.0.1:5000"))

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


@app.route("/categorize", methods=["POST"])
def categorize():
    try:
        payload = request.get_json() or {}
        transactions = payload.get("transactions")

        if not transactions or not isinstance(transactions, list):
            return jsonify({
                "success": False,
                "error": "transactions missing or empty"
            }), 400

        # Validate input
        for index, tx in enumerate(transactions):
            if not isinstance(tx, dict):
                return jsonify({
                    "success": False,
                    "error": f"Invalid transaction at index {index}"
                }), 400

            if "description" not in tx:
                tx["description"] = ""

        # Categorize all transactions
        updated = apply_categorization(transactions)

        # Final validation before returning
        valid_categories = {
            "Revenue",
            "Inventory",
            "Utilities",
            "Rent",
            "Salaries",
            "Transport",
            "Marketing",
            "Maintenance",
            "Personal",
            "Food",
            "Other"
        }

        for tx in updated:
            if tx.get("category") not in valid_categories:
                tx["category"] = "Other"

            try:
                tx["confidence_score"] = float(
                    tx.get("confidence_score", 0.50)
                )
            except (TypeError, ValueError):
                tx["confidence_score"] = 0.50

            tx["confidence_score"] = max(
                0.0,
                min(1.0, tx["confidence_score"])
            )

        return jsonify({
            "success": True,
            "transactions": updated,
            "count": len(updated)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/save-transactions", methods=["POST"])
def save_transactions():
    try:
        payload = request.get_json() or {}
        transactions = payload.get("transactions")

        if not transactions or not isinstance(transactions, list):
            return jsonify({
                "success": False,
                "error": "transactions missing or empty"
            }), 400

        # Validate all transactions BEFORE saving anything
        valid_categories = {
            "Revenue",
            "Inventory",
            "Utilities",
            "Rent",
            "Salaries",
            "Transport",
            "Marketing",
            "Maintenance",
            "Personal",
            "Food",
            "Other"
        }

        for index, tx in enumerate(transactions):
            if not isinstance(tx, dict):
                return jsonify({
                    "success": False,
                    "error": f"Invalid transaction at index {index}"
                }), 400

            # Amount must exist and be numeric
            if tx.get("amount") is None:
                return jsonify({
                    "success": False,
                    "error": f"Amount missing at index {index}"
                }), 400

            try:
                amount = float(tx["amount"])
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "error": f"Invalid amount at index {index}"
                }), 400

            if not amount == amount or amount in (float("inf"), float("-inf")):
                return jsonify({
                    "success": False,
                    "error": f"Invalid amount at index {index}"
                }), 400

            # Category must be one of the allowed categories
            category = tx.get("category")
            if category not in valid_categories:
                return jsonify({
                    "success": False,
                    "error": f"Invalid category at index {index}"
                }), 400

            # Confidence score is optional, but must be numeric and 0-1
            if "confidence_score" in tx:
                try:
                    confidence = float(tx["confidence_score"])
                except (TypeError, ValueError):
                    return jsonify({
                        "success": False,
                        "error": f"Invalid confidence_score at index {index}"
                    }), 400

                if (
                    confidence != confidence
                    or confidence < 0.0
                    or confidence > 1.0
                    or confidence in (float("inf"), float("-inf"))
                ):
                    return jsonify({
                        "success": False,
                        "error": f"Invalid confidence_score at index {index}"
                    }), 400

                tx["confidence_score"] = confidence

            tx["amount"] = amount

        # Save the complete batch to the OFFICIAL transactions table
        resp = (
            supabase
            .table("transactions")
            .insert(transactions)
            .execute()
        )

        if isinstance(resp, dict):
            rows = resp.get("data") or []
        else:
            rows = getattr(resp, "data", None) or []

        ids = [
            row.get("id")
            for row in rows
            if isinstance(row, dict) and row.get("id")
        ]

        return jsonify({
            "success": True,
            "saved": True,
            "count": len(rows),
            "ids": ids
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "saved": False,
            "error": str(e)
        }), 500

@app.route("/correct-category", methods=["POST"])
def correct_category():
    try:
        payload = request.get_json() or {}

        transaction_id = payload.get("transaction_id")
        new_category = payload.get("new_category")

        if not transaction_id or not new_category:
            return jsonify({
                "success": False,
                "error": "transaction_id and new_category required"
            }), 400

        # Validate category
        valid_categories = {
            "Revenue",
            "Inventory",
            "Utilities",
            "Rent",
            "Salaries",
            "Transport",
            "Marketing",
            "Maintenance",
            "Personal",
            "Food",
            "Other"
        }

        if new_category not in valid_categories:
            return jsonify({
                "success": False,
                "error": "Invalid category"
            }), 400

        response = (
            supabase
            .table("transactions")
            .update({
                "category": new_category
            })
            .eq("id", transaction_id)
            .execute()
        )

        return jsonify({
            "success": True,
            "updated": True
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/transactions", methods=["GET"])
def get_transactions():
    try:
        category = request.args.get("category")
        ttype = request.args.get("type")
        limit = int(request.args.get("limit") or 50)

        query = (
            supabase
            .table("transactions")
            .select("*")
            .order("created_at", {"ascending": False})
        )

        if category:
            query = query.eq("category", category)

        if ttype:
            query = query.eq("type", ttype)

        if limit:
            query = query.limit(limit)

        resp = query.execute()

        if isinstance(resp, dict):
            rows = resp.get("data") or []
        else:
            rows = getattr(resp, "data", None) or []

        return jsonify({
            "success": True,
            "transactions": rows,
            "count": len(rows)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/categories/summary", methods=["GET"])
def categories_summary():
    try:
        resp = supabase.table("transactions").select("*").execute()
        if isinstance(resp, dict):
            rows = resp.get('data') or []
        else:
            rows = getattr(resp, 'data', None) or []

        summary = {}
        for r in rows:
            cat = r.get('category') or 'Other'
            amt = r.get('amount') or 0
            try:
                val = float(amt)
            except Exception:
                try:
                    val = float(str(amt))
                except Exception:
                    val = 0
            summary[cat] = summary.get(cat, 0) + val

        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/summary", methods=["GET"])
def overall_summary():
    try:
        date_filter = request.args.get('date')
        query = supabase.table("transactions").select("*")
        if date_filter:
            query = query.eq('date', date_filter)
        resp = query.execute()
        if isinstance(resp, dict):
            rows = resp.get('data') or []
        else:
            rows = getattr(resp, 'data', None) or []

        total_revenue = 0.0
        total_expenses = 0.0
        for r in rows:
            amt = r.get('amount') or 0
            try:
                val = float(amt)
            except Exception:
                try:
                    val = float(str(amt))
                except Exception:
                    val = 0
            ttype = (r.get('type') or '').lower()
            if ttype == 'income':
                total_revenue += val
            elif ttype == 'expense':
                total_expenses += val
        net_profit = total_revenue - total_expenses
        return jsonify({
            "success": True,
            "summary": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": net_profit,
                "transaction_count": len(rows)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "PocketCFO API is running"})


@app.route("/auth/config", methods=["GET"])
def auth_config():
    """Return only the Supabase browser configuration, never a service key."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        return jsonify({"success": False, "message": "Supabase is not configured"}), 503

    try:
        encoded_payload = supabase_key.split(".")[1]
        encoded_payload += "=" * (-len(encoded_payload) % 4)
        role = json.loads(
            base64.urlsafe_b64decode(encoded_payload).decode("utf-8")
        ).get("role")
    except (IndexError, ValueError, UnicodeDecodeError, binascii.Error):
        role = None

    if role != "anon":
        return jsonify({
            "success": False,
            "message": "A public Supabase anon key is required for browser authentication",
        }), 500

    return jsonify({
        "success": True,
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_key,
    })


@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')


@app.route("/<path:path>", methods=["GET"])


@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    if os.path.isfile(os.path.join(os.path.dirname(__file__), path)):
        return send_from_directory(os.path.dirname(__file__), path)
    return send_from_directory(os.path.dirname(__file__), 'index.html')


@app.route("/parse", methods=["POST"])
def parse():
    try:
        payload = request.get_json() or {}
        text = payload.get("text", "").strip()
        if not text:
            return jsonify({"success": False, "error": "text is required"}), 400

        from parser import parse_transaction
        parsed = parse_transaction(text)

        return jsonify({
            "success": True,
            "parsed": parsed,
            "count": len(parsed)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=os.getenv('DEBUG', 'false').lower() == 'true')
