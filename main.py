import sqlite3
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox
import csv

DB_PATH = "todo.db"

def get_conn(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        due_date TEXT,
        priority INTEGER DEFAULT 3,
        status TEXT DEFAULT 'open'
    )
    """)
    conn.commit()
    return conn

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def add_task_db(title, description, due_date, priority):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, description, created_at, due_date, priority, status) VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, now_utc_iso(), due_date or "", int(priority), "open")
    )
    conn.commit()
    conn.close()

def update_task_db(task_id, title, description, due_date, priority, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET title=?, description=?, due_date=?, priority=?, status=? WHERE id=?",
        (title, description, due_date or "", int(priority), status, int(task_id))
    )
    conn.commit()
    conn.close()

def delete_task_db(task_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=?", (int(task_id),))
    conn.commit()
    conn.close()

def list_tasks_db(search=None, order_by="id"):
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT * FROM tasks"
    params = []
    if search:
        q += " WHERE title LIKE ? OR description LIKE ?"
        params.extend((f"%{search}%", f"%{search}%"))
    if order_by in ("due_date", "priority", "created_at", "status", "title", "id"):
        q += f" ORDER BY {order_by}"
    df = cur.execute(q, params).fetchall()
    conn.close()
    return df

def export_csv(path="tasks_export.csv"):
    rows = list_tasks_db(order_by="id")
    if not rows:
        return None
    with open(path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id","title","description","created_at","due_date","priority","status"])
        for r in rows:
            writer.writerow([r["id"], r["title"], r["description"], r["created_at"], r["due_date"], r["priority"], r["status"]])
    return path

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер задач")
        self.frame_left = ttk.Frame(root, padding=10)
        self.frame_left.grid(row=0, column=0, sticky="ns")
        self.frame_right = ttk.Frame(root, padding=10)
        self.frame_right.grid(row=0, column=1, sticky="nsew")
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.order_var = tk.StringVar(value="due_date")
        self._build_controls()
        self._build_tree()
        self._populate_tree()

    def _build_controls(self):
        ttk.Label(self.frame_left, text="Название").grid(row=0, column=0, sticky="w")
        self.e_title = ttk.Entry(self.frame_left, width=30)
        self.e_title.grid(row=1, column=0, pady=2)

        ttk.Label(self.frame_left, text="Описание").grid(row=2, column=0, sticky="w")
        self.e_desc = tk.Text(self.frame_left, width=30, height=6)
        self.e_desc.grid(row=3, column=0, pady=2)

        ttk.Label(self.frame_left, text="Срок (ГГГГ-ММ-ДД)").grid(row=4, column=0, sticky="w")
        self.e_due = ttk.Entry(self.frame_left, width=30)
        self.e_due.grid(row=5, column=0, pady=2)

        ttk.Label(self.frame_left, text="Приоритет (1-5)").grid(row=6, column=0, sticky="w")
        self.e_prio = ttk.Spinbox(self.frame_left, from_=1, to=5, width=5)
        self.e_prio.set(3)
        self.e_prio.grid(row=7, column=0, pady=2, sticky="w")

        self.status_var = tk.StringVar(value="open")
        ttk.Label(self.frame_left, text="Статус").grid(row=8, column=0, sticky="w")
        # keep internal status values as in DB: open, in_progress, done
        self.cb_status = ttk.Combobox(self.frame_left, values=["open","in_progress","done"], textvariable=self.status_var, state="readonly", width=27)
        self.cb_status.grid(row=9, column=0, pady=2)

        self.btn_add = ttk.Button(self.frame_left, text="Создать", command=self.create_task)
        self.btn_add.grid(row=10, column=0, sticky="ew", pady=(6,2))
        self.btn_update = ttk.Button(self.frame_left, text="Обновить", command=self.update_task)
        self.btn_update.grid(row=11, column=0, sticky="ew", pady=2)
        self.btn_delete = ttk.Button(self.frame_left, text="Удалить", command=self.delete_task)
        self.btn_delete.grid(row=12, column=0, sticky="ew", pady=2)
        self.btn_mark_done = ttk.Button(self.frame_left, text="Пометить выполненным", command=self.mark_done)
        self.btn_mark_done.grid(row=13, column=0, sticky="ew", pady=2)
        self.btn_export = ttk.Button(self.frame_left, text="Экспорт CSV", command=self.export_csv_action)
        self.btn_export.grid(row=14, column=0, sticky="ew", pady=(10,2))

        ttk.Label(self.frame_left, text="Поиск").grid(row=15, column=0, sticky="w", pady=(8,0))
        self.e_search = ttk.Entry(self.frame_left, textvariable=self.search_var, width=30)
        self.e_search.grid(row=16, column=0, pady=2)
        self.btn_search = ttk.Button(self.frame_left, text="Найти", command=self.search_action)
        self.btn_search.grid(row=17, column=0, sticky="ew", pady=2)
        ttk.Label(self.frame_left, text="Сортировать по").grid(row=18, column=0, sticky="w", pady=(8,0))
        self.cb_order = ttk.Combobox(self.frame_left, values=["id","title","created_at","due_date","priority","status"], textvariable=self.order_var, state="readonly", width=27)
        self.cb_order.grid(row=19, column=0, pady=2)
        self.btn_refresh = ttk.Button(self.frame_left, text="Обновить", command=self._populate_tree)
        self.btn_refresh.grid(row=20, column=0, sticky="ew", pady=(6,2))

    def _build_tree(self):
        columns = ("id","title","due_date","priority","status","created_at")
        self.tree = ttk.Treeview(self.frame_right, columns=columns, show="headings", selectmode="browse")
        headings_map = {
            "id": "ID",
            "title": "Название",
            "due_date": "Срок",
            "priority": "Приоритет",
            "status": "Статус",
            "created_at": "Создано"
        }
        for col in columns:
            self.tree.heading(col, text=headings_map.get(col, col))
            self.tree.column(col, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.frame_right.rowconfigure(0, weight=1)
        self.frame_right.columnconfigure(0, weight=1)
        vsb = ttk.Scrollbar(self.frame_right, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def _populate_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = list_tasks_db(order_by=self.order_var.get(), search=self.search_var.get().strip() or None)
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["title"], r["due_date"], r["priority"], r["status"], r["created_at"]))

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return None
        return vals[0]

    def on_tree_select(self, event):
        sid = self._get_selected_id()
        if not sid:
            return
        conn = get_conn()
        cur = conn.cursor()
        row = cur.execute("SELECT * FROM tasks WHERE id=?", (int(sid),)).fetchone()
        conn.close()
        if not row:
            return
        self.e_title.delete(0, tk.END)
        self.e_title.insert(0, row["title"])
        self.e_desc.delete("1.0", tk.END)
        self.e_desc.insert("1.0", row["description"] or "")
        self.e_due.delete(0, tk.END)
        self.e_due.insert(0, row["due_date"] or "")
        self.e_prio.set(row["priority"])
        self.status_var.set(row["status"])

    def create_task(self):
        title = self.e_title.get().strip()
        if not title:
            messagebox.showwarning("Проверка", "Требуется название")
            return
        desc = self.e_desc.get("1.0", tk.END).strip()
        due = self.e_due.get().strip()
        prio = self.e_prio.get()
        try:
            if due:
                datetime.fromisoformat(due)
        except Exception:
            messagebox.showwarning("Проверка", "Срок должен быть в формате ГГГГ-ММ-ДД")
            return
        try:
            add_task_db(title, desc, due, int(prio))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        self._populate_tree()
        self._clear_inputs()

    def update_task(self):
        sid = self._get_selected_id()
        if not sid:
            messagebox.showwarning("Выберите", "Выберите задачу для обновления")
            return
        title = self.e_title.get().strip()
        if not title:
            messagebox.showwarning("Проверка", "Требуется название")
            return
        desc = self.e_desc.get("1.0", tk.END).strip()
        due = self.e_due.get().strip()
        prio = self.e_prio.get()
        status = self.status_var.get()
        try:
            if due:
                datetime.fromisoformat(due)
        except Exception:
            messagebox.showwarning("Проверка", "Срок должен быть в формате ГГГГ-ММ-ДД")
            return
        try:
            update_task_db(sid, title, desc, due, int(prio), status)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        self._populate_tree()
        self._clear_inputs()

    def delete_task(self):
        sid = self._get_selected_id()
        if not sid:
            messagebox.showwarning("Выберите", "Выберите задачу для удаления")
            return
        if not messagebox.askyesno("Подтвердите", "Удалить выбранную задачу?"):
            return
        try:
            delete_task_db(sid)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        self._populate_tree()
        self._clear_inputs()

    def mark_done(self):
        sid = self._get_selected_id()
        if not sid:
            messagebox.showwarning("Выберите", "Выберите задачу для пометки как выполненная")
            return
        try:
            update_task_db(sid, self.e_title.get().strip() or "Без названия", self.e_desc.get("1.0", tk.END).strip(), self.e_due.get().strip(), int(self.e_prio.get()), "done")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
        self._populate_tree()
        self._clear_inputs()

    def export_csv_action(self):
        path = export_csv()
        if path:
            messagebox.showinfo("Экспорт", f"Экспортирован в {path}")
        else:
            messagebox.showinfo("Экспорт", "Нет задач для экспорта")

    def search_action(self):
        self._populate_tree()

    def _clear_inputs(self):
        self.e_title.delete(0, tk.END)
        self.e_desc.delete("1.0", tk.END)
        self.e_due.delete(0, tk.END)
        self.e_prio.set(3)
        self.status_var.set("open")
        self.tree.selection_remove(self.tree.selection())

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = TodoApp(root)
    root.geometry("900x500")
    root.mainloop()
