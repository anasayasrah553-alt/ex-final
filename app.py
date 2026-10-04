from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename


app = Flask(__name__)


# ==========================================
# إعدادات المشروع
# ==========================================

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================
# الاتصال بقاعدة البيانات
# ==========================================

def get_db():

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================
# إنشاء الجداول
# ==========================================

def create_tables():

    conn = get_db()


    # جدول الأغراض

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            category TEXT NOT NULL,

            description TEXT NOT NULL,

            estimated_value REAL NOT NULL,

            condition TEXT NOT NULL,

            wanted TEXT NOT NULL,

            location TEXT NOT NULL,

            owner TEXT NOT NULL,

            phone TEXT NOT NULL,

            image TEXT,

            status TEXT DEFAULT 'available'

        )
    """)


    # جدول طلبات المبادلة

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exchange_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            requester_name TEXT NOT NULL,

            requester_phone TEXT NOT NULL,

            message TEXT,

            status TEXT DEFAULT 'pending',

            FOREIGN KEY (item_id)
            REFERENCES items(id)

        )
    """)


    conn.commit()

    conn.close()


# ==========================================
# الصفحة الرئيسية
# ==========================================

@app.route("/")
def home():

    conn = get_db()

    items = conn.execute("""
        SELECT *
        FROM items

        WHERE status = 'available'

        ORDER BY id DESC

        LIMIT 6

    """).fetchall()

    conn.close()

    return render_template(
        "home.html",
        items=items
    )


# ==========================================
# إضافة غرض
# ==========================================

@app.route("/add", methods=["GET", "POST"])
def add_item():

    if request.method == "POST":

        name = request.form["name"]

        category = request.form["category"]

        description = request.form["description"]

        estimated_value = request.form["estimated_value"]

        condition = request.form["condition"]

        wanted = request.form["wanted"]

        location = request.form["location"]

        owner = request.form["owner"]

        phone = request.form["phone"]


        # الصورة

        image = request.files["image"]

        filename = ""


        if image and image.filename:

            original_name = secure_filename(
                image.filename
            )

            extension = os.path.splitext(
                original_name
            )[1]

            filename = uuid.uuid4().hex + extension

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )


        # حفظ الغرض

        conn = get_db()

        conn.execute("""
            INSERT INTO items (

                name,
                category,
                description,
                estimated_value,
                condition,
                wanted,
                location,
                owner,
                phone,
                image,
                status

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            name,
            category,
            description,
            estimated_value,
            condition,
            wanted,
            location,
            owner,
            phone,
            filename,
            "available"

        ))


        conn.commit()

        conn.close()


        return redirect(
            url_for("show_items")
        )


    return render_template(
        "add_item.html"
    )


# ==========================================
# عرض الأغراض
# ==========================================

@app.route("/items")
def show_items():

    search = request.args.get(
        "search",
        ""
    )

    category = request.args.get(
        "category",
        ""
    )


    conn = get_db()


    query = """
        SELECT *
        FROM items
        WHERE 1=1
    """


    values = []


    # البحث

    if search:

        query += """
            AND (
                name LIKE ?
                OR description LIKE ?
                OR wanted LIKE ?
            )
        """

        search_value = "%" + search + "%"

        values.extend([
            search_value,
            search_value,
            search_value
        ])


    # التصنيف

    if category:

        query += """
            AND category = ?
        """

        values.append(category)


    query += """
        ORDER BY id DESC
    """


    items = conn.execute(
        query,
        values
    ).fetchall()


    conn.close()


    return render_template(
        "items.html",
        items=items,
        search=search,
        category=category
    )


# ==========================================
# تعديل الغرض
# ==========================================

@app.route(
    "/edit/<int:item_id>",
    methods=["GET", "POST"]
)
def edit_item(item_id):

    conn = get_db()


    item = conn.execute("""
        SELECT *
        FROM items
        WHERE id = ?

    """, (item_id,)).fetchone()


    if item is None:

        conn.close()

        return "الغرض غير موجود"


    if request.method == "POST":

        name = request.form["name"]

        category = request.form["category"]

        description = request.form["description"]

        estimated_value = request.form["estimated_value"]

        condition = request.form["condition"]

        wanted = request.form["wanted"]

        location = request.form["location"]

        owner = request.form["owner"]

        phone = request.form["phone"]


        # الصورة الجديدة

        image = request.files["image"]

        filename = item["image"]


        if image and image.filename:

            original_name = secure_filename(
                image.filename
            )

            extension = os.path.splitext(
                original_name
            )[1]

            filename = uuid.uuid4().hex + extension


            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )


        conn.execute("""
            UPDATE items

            SET

                name = ?,

                category = ?,

                description = ?,

                estimated_value = ?,

                condition = ?,

                wanted = ?,

                location = ?,

                owner = ?,

                phone = ?,

                image = ?

            WHERE id = ?

        """, (

            name,
            category,
            description,
            estimated_value,
            condition,
            wanted,
            location,
            owner,
            phone,
            filename,
            item_id

        ))


        conn.commit()

        conn.close()


        return redirect(
            url_for("show_items")
        )


    conn.close()


    return render_template(
        "edit_item.html",
        item=item
    )


# ==========================================
# حذف الغرض
# ==========================================

@app.route(
    "/delete/<int:item_id>"
)
def delete_item(item_id):

    conn = get_db()


    # حذف طلبات المبادلة المتعلقة بالغرض

    conn.execute("""
        DELETE FROM exchange_requests

        WHERE item_id = ?

    """, (item_id,))


    # الحصول على الصورة

    item = conn.execute("""
        SELECT image
        FROM items
        WHERE id = ?

    """, (item_id,)).fetchone()


    if item:

        image_name = item["image"]


        if image_name:

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_name
            )


            if os.path.exists(image_path):

                os.remove(image_path)


        # حذف الغرض

        conn.execute("""
            DELETE FROM items
            WHERE id = ?

        """, (item_id,))


        conn.commit()


    conn.close()


    return redirect(
        url_for("show_items")
    )


# ==========================================
# طلب مبادلة
# ==========================================

@app.route(
    "/request_exchange/<int:item_id>",
    methods=["GET", "POST"]
)
def request_exchange(item_id):

    conn = get_db()


    item = conn.execute("""
        SELECT *
        FROM items
        WHERE id = ?

    """, (item_id,)).fetchone()


    if item is None:

        conn.close()

        return "الغرض غير موجود"


    if item["status"] != "available":

        conn.close()

        return "هذا الغرض تمت مبادلته مسبقًا"


    if request.method == "POST":

        requester_name = request.form[
            "requester_name"
        ]

        requester_phone = request.form[
            "requester_phone"
        ]

        message = request.form[
            "message"
        ]


        conn.execute("""
            INSERT INTO exchange_requests (

                item_id,

                requester_name,

                requester_phone,

                message,

                status

            )

            VALUES (?, ?, ?, ?, ?)

        """, (

            item_id,

            requester_name,

            requester_phone,

            message,

            "pending"

        ))


        conn.commit()

        conn.close()


        return redirect(
            url_for("show_items")
        )


    conn.close()


    return render_template(
        "request_exchange.html",
        item=item
    )


# ==========================================
# عرض طلبات المبادلة
# ==========================================

@app.route("/requests")
def requests():

    conn = get_db()


    exchange_requests = conn.execute("""
        SELECT

            exchange_requests.*,

            items.name AS item_name,

            items.owner AS owner_name

        FROM exchange_requests

        JOIN items

        ON exchange_requests.item_id = items.id

        ORDER BY exchange_requests.id DESC

    """).fetchall()


    conn.close()


    return render_template(
        "requests.html",
        requests=exchange_requests
    )


# ==========================================
# قبول طلب المبادلة
# ==========================================

@app.route(
    "/accept_request/<int:request_id>"
)
def accept_request(request_id):

    conn = get_db()


    exchange_request = conn.execute("""
        SELECT *
        FROM exchange_requests

        WHERE id = ?

    """, (request_id,)).fetchone()


    if exchange_request:

        item_id = exchange_request["item_id"]


        # قبول الطلب

        conn.execute("""
            UPDATE exchange_requests

            SET status = 'accepted'

            WHERE id = ?

        """, (request_id,))


        # جعل الغرض مبادل

        conn.execute("""
            UPDATE items

            SET status = 'exchanged'

            WHERE id = ?

        """, (item_id,))


        # رفض باقي الطلبات

        conn.execute("""
            UPDATE exchange_requests

            SET status = 'rejected'

            WHERE item_id = ?

            AND id != ?

            AND status = 'pending'

        """, (

            item_id,

            request_id

        ))


        conn.commit()


    conn.close()


    return redirect(
        url_for("requests")
    )


# ==========================================
# رفض طلب المبادلة
# ==========================================

@app.route(
    "/reject_request/<int:request_id>"
)
def reject_request(request_id):

    conn = get_db()


    conn.execute("""
        UPDATE exchange_requests

        SET status = 'rejected'

        WHERE id = ?

    """, (request_id,))


    conn.commit()

    conn.close()


    return redirect(
        url_for("requests")
    )


# ==========================================
# صفحة About
# ==========================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# ==========================================
# تشغيل البرنامج
# ==========================================

if __name__ == "__main__":

    create_tables()

    app.run(
        debug=True
    )