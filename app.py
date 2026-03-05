import os
import json
import requests
import openai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ==================== CONFIG ====================
BACKLOG_API_KEY = os.environ.get("BACKLOG_API_KEY", "YOUR_API_KEY")
BACKLOG_BASE_URL = os.environ.get("BACKLOG_BASE_URL", "https://YOUR_SPACE.backlog.com/api/v2")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_KEY")

# Danh sách user được trigger auto-translate
ALLOWED_USERS = [
    {"name": "Nguyen Dieu Linh", "email": "linh.nguyen2@amela.vn"},
    {"name": "Phan Thanh Thuy",  "email": "thuy.phanthithanh@amela.vn"},
]

# Rule assign theo loại ticket
ASSIGN_RULES = [
    {
        "category": "FE",
        "description": "Ticket chỉ liên quan Frontend (UI, CSS, React, Vue, HTML, JS, màn hình)",
        "backlog_user_id": 780642,
        "name": "Duyen.Ngo",
    },
    {
        "category": "BE",
        "description": "Ticket chỉ liên quan Backend (API, database, server logic, Ruby, Java, Python)",
        "backlog_user_id": 111849,
        "name": "Le Quoc Dat",
    },
    {
        "category": "INFRA",
        "description": "Ticket liên quan infra, crawl, hệ thống, cần estimate công",
        "backlog_user_id": 272725,
        "name": "tien.pham",
    },
    {
        "category": "QA",
        "description": "Ticket cần test, cần tái hiện lỗi, là bug report",
        "backlog_user_id": 350533,
        "name": "Nguyễn Quỳnh",
    },
    {
        "category": "UNKNOWN",
        "description": "Không xác định được loại ticket hoặc không thuộc các loại trên",
        "backlog_user_id": 452545,
        "name": "Phan Thanh Thuy",
    },
]

# Map category → assignee (để lookup nhanh)
CATEGORY_MAP = {rule["category"]: rule for rule in ASSIGN_RULES}
# ================================================


def analyze_and_translate(summary: str, description: str) -> dict:
    """
    Gọi OpenAI để:
    1. Dịch JP → VI
    2. Phân loại ticket (FE / BE / INFRA / QA / UNKNOWN)
    3. Đề xuất Next Action
    Trả về dict: { "translation": str, "category": str, "next_action": str }
    """
    # Khởi tạo OpenAI client (Lưu ý thư viện openai 1.x)
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Build danh sách category + mô tả để GPT hiểu rule
    rule_descriptions = "\n".join(
        [f'- "{r["category"]}": {r["description"]}' for r in ASSIGN_RULES]
    )

    prompt = f"""Bạn là trợ lý dự án. Hãy thực hiện 3 việc sau với ticket Backlog này:

1. **Dịch** toàn bộ nội dung sang tiếng Việt (nếu đã là VI thì giữ nguyên).
2. **Phân loại** ticket theo đúng 1 trong các category sau:
{rule_descriptions}
3. **Đề xuất Next Action** cụ thể (1-3 bước ngắn gọn).

---
[SUMMARY]: {summary}
[DESCRIPTION]: {description}
---

Trả về JSON hợp lệ theo đúng format sau (không thêm gì ngoài JSON):
{{
  "translation": "<bản dịch tiếng Việt của summary + description>",
  "category": "<FE | BE | INFRA | QA | UNKNOWN>",
  "next_action": "<các bước next action>"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o", # Sử dụng gpt-4o tốt hơn gpt-4 cho việc tạo JSON
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # Giảm temperature để phân loại ổn định hơn
    )

    raw = response.choices[0].message.content.strip()

    # Thường GPT có thể trả về JSON bọc trong markdown ```json ... ```, do đó loại bỏ chúng nếu có:
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    # Parse JSON từ GPT
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback nếu GPT trả về không chuẩn JSON
        result = {
            "translation": raw,
            "category": "UNKNOWN",
            "next_action": "Vui lòng xem xét và xác định next action thủ công.",
        }

    # Đảm bảo category hợp lệ
    if result.get("category") not in CATEGORY_MAP:
        result["category"] = "UNKNOWN"

    return result


def assign_issue(issue_id: int, user_id: int) -> None:
    """Assign issue cho user trên Backlog."""
    if not user_id:
        return
    url    = f"{BACKLOG_BASE_URL}/issues/{issue_id}"
    params = {"apiKey": BACKLOG_API_KEY}
    data   = {"assigneeId": user_id}
    res    = requests.patch(url, params=params, data=data)
    # Bỏ qua dòng res.raise_for_status() để tránh sập server nếu id assign sai lệch với trên project
    if res.status_code != 200:
        print(f"Failed to assign issue {issue_id} to user {user_id}: {res.text}")


def add_comment(issue_id: int, comment: str) -> None:
    """Thêm comment vào issue trên Backlog."""
    if not issue_id:
        return
    url    = f"{BACKLOG_BASE_URL}/issues/{issue_id}/comments"
    params = {"apiKey": BACKLOG_API_KEY}
    data   = {"content": comment}
    res    = requests.post(url, params=params, data=data)
    if res.status_code != 200:
        print(f"Failed to add comment to issue {issue_id}: {res.text}")


def is_allowed_user(created_user: dict) -> bool:
    """Kiểm tra ticket có được tạo bởi user trong danh sách không."""
    user_name  = created_user.get("name", "")
    user_email = created_user.get("mailAddress", "")
    for allowed in ALLOWED_USERS:
        if allowed["email"] == user_email or allowed["name"] == user_name:
            return True
    return False

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "running"}), 200

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    payload = request.json
    
    if not payload:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    # Chỉ xử lý event Issue Created (type = 1)
    if payload.get("type") != 1:
        return jsonify({"status": "skipped", "reason": "not issue_created"})

    created_user = payload.get("createdUser", {})
    issue        = payload.get("content", {})

    # ── Kiểm tra user ──────────────────────────────────────────
    if not is_allowed_user(created_user):
        return jsonify({
            "status": "skipped",
            "reason": f"user '{created_user.get('name')}' not in allowed list",
        })

    # ── Lấy thông tin ticket ───────────────────────────────────
    issue_id  = issue.get("id")
    summary   = issue.get("summary", "")
    desc      = issue.get("description", "")

    try:
        # ── Phân tích: Dịch + Phân loại + Next Action ─────────────
        analysis = analyze_and_translate(summary, desc)
        category    = analysis["category"]
        translation = analysis["translation"]
        next_action = analysis["next_action"]

        # ── Xác định assignee ──────────────────────────────────────
        assignee = CATEGORY_MAP[category]

        # ── Assign issue ───────────────────────────────────────────
        assign_issue(issue_id, assignee["backlog_user_id"])

        # ── Build comment ──────────────────────────────────────────
        category_labels = {
            "FE":      "🎨 Frontend",
            "BE":      "⚙️ Backend",
            "INFRA":   "🏗️ Infra / System",
            "QA":      "🐛 QA / Bug",
            "UNKNOWN": "❓ Chưa xác định",
        }
        comment = f"""🇻🇳 **[Bản dịch tự động JP → VI]**

{translation}

---

📌 **Next Action:**
{next_action}

---

🏷️ **Phân loại:** {category_labels.get(category, category)}
👤 **Assigned to:** {assignee["name"]}
🤖 _Auto-processed by Bot | Triggered by: {created_user.get("name")}_"""

        add_comment(issue_id, comment)

        return jsonify({
            "status":      "ok",
            "issue_id":    issue_id,
            "category":    category,
            "assigned_to": assignee["name"],
            "triggered_by": created_user.get("name"),
        })
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
