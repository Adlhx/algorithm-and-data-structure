import tkinter as tk
from tkinter import ttk, messagebox
import json, os
from dataclasses import dataclass, field
from typing import Dict, Set, List, Tuple, Optional


# DATA CLASSES


@dataclass
class Book:
    book_id: str
    title: str
    genre: str


@dataclass
class User:
    user_id: str
    name: str
    purchased_books: Set[str] = field(default_factory=set)


# RECOMMENDER SYSTEM (COLLABORATIVE FILTERING)


class RecommenderSystem:
    def __init__(self, users: Dict[str, User], books: Dict[str, Book]):
        self.users = users
        self.books = books

    @staticmethod
    def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
        """Jaccard = |A ∩ B| / |A ∪ B|"""
        if not a and not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    def most_similar_users(self, target_user_id: str, top_k: int = 3) -> List[Tuple[User, float]]:
        """Find top-k users most similar to target using Jaccard on purchased_books."""
        target = self.users[target_user_id]
        sims: List[Tuple[User, float]] = []
        for uid, user in self.users.items():
            if uid == target_user_id:
                continue
            sim = self.jaccard_similarity(target.purchased_books, user.purchased_books)
            if sim > 0:
                sims.append((user, sim))
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]

    def recommend_books(self, target_user_id: str, max_recs: int = 5) -> List[Tuple[Book, float]]:
        """
        Collaborative filtering:
        - Find similar users
        - Collect their books not owned by target
        - Weight by similarity
        """
        target = self.users[target_user_id]
        similar_users = self.most_similar_users(target_user_id)
        score_map: Dict[str, float] = {}

        for user, sim in similar_users:
            for book_id in user.purchased_books:
                if book_id in target.purchased_books:
                    continue
                score_map[book_id] = score_map.get(book_id, 0.0) + sim

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        recs: List[Tuple[Book, float]] = []
        for bid, score in ranked[:max_recs]:
            book = self.books.get(bid)
            if book:
                recs.append((book, score))
        return recs

    def time_complexity_string(self) -> str:
        U = len(self.users)
        B = len(self.books)
        return f"O(U × B) ≈ O({U} × {B}) = O({U * B})"


# DEFAULT DATA (used if JSON missing/broken)


DEFAULT_USERS = [
    {"user_id": "U1", "name": "Alice", "purchased_books": ["B1", "B2"]},
    {"user_id": "U2", "name": "Bob", "purchased_books": ["B2", "B3", "B4"]},
    {"user_id": "U3", "name": "Charlie", "purchased_books": ["B1", "B4"]},
]

DEFAULT_BOOKS = [
    {"book_id": "B1", "title": "Python Made Easy", "genre": "Programming"},
    {"book_id": "B2", "title": "AI Basics", "genre": "AI"},
    {"book_id": "B3", "title": "Deep Learning", "genre": "AI"},
    {"book_id": "B4", "title": "Story of Night", "genre": "Fiction"},
]



# JSON LOAD/SAVE WITH ERROR HANDLING


def get_data_paths() -> Tuple[str, str]:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "users.json"), os.path.join(base, "books.json")


def save_users_json(users_data: List[Dict], path: Optional[str] = None) -> None:
    if path is None:
        path, _ = get_data_paths()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"users": users_data}, f, indent=2)


def save_books_json(books_data: List[Dict], path: Optional[str] = None) -> None:
    if path is None:
        _, path = get_data_paths()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"books": books_data}, f, indent=2)


def load_data() -> Tuple[Dict[str, User], Dict[str, Book], str]:
    users_path, books_path = get_data_paths()
    msg_parts: List[str] = []

    # Load users
    try:
        with open(users_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and "users" in raw:
            users_data = raw["users"]
        elif isinstance(raw, list):
            users_data = raw
        else:
            raise ValueError("invalid users structure")
    except Exception as e:
        users_data = DEFAULT_USERS
        msg_parts.append(f"users.json issue ({e}) – using defaults and rewriting file.")
        save_users_json(users_data, users_path)

    # Load books
    try:
        with open(books_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and "books" in raw:
            books_data = raw["books"]
        elif isinstance(raw, list):
            books_data = raw
        else:
            raise ValueError("invalid books structure")
    except Exception as e:
        books_data = DEFAULT_BOOKS
        msg_parts.append(f"books.json issue ({e}) – using defaults and rewriting file.")
        save_books_json(books_data, books_path)

    users: Dict[str, User] = {}
    for u in users_data:
        users[u["user_id"]] = User(
            user_id=u["user_id"],
            name=u.get("name", u["user_id"]),
            purchased_books=set(u.get("purchased_books", [])),
        )

    books: Dict[str, Book] = {}
    for b in books_data:
        books[b["book_id"]] = Book(
            book_id=b["book_id"],
            title=b.get("title", b["book_id"]),
            genre=b.get("genre", "Unknown"),
        )

    return users, books, "\n".join(msg_parts)


def save_all(users: Dict[str, User], books: Dict[str, Book]) -> None:
    users_data = [
        {
            "user_id": u.user_id,
            "name": u.name,
            "purchased_books": sorted(list(u.purchased_books)),
        }
        for u in users.values()
    ]
    books_data = [
        {"book_id": b.book_id, "title": b.title, "genre": b.genre}
        for b in books.values()
    ]
    upath, bpath = get_data_paths()
    save_users_json(users_data, upath)
    save_books_json(books_data, bpath)


# GUI


class BookstoreGUI:
    def __init__(self, root: tk.Tk, recommender: RecommenderSystem, users: Dict[str, User], books: Dict[str, Book]):
        self.root = root
        self.rec = recommender
        self.users = users
        self.books = books

        root.title("Book Recommendation System")
        root.geometry("1300x750")  # large fixed size
        root.configure(bg="#1a1a1a")

        self.build_gui()

    # BUILD GUI 

    def build_gui(self):
        title = tk.Label(
            self.root,
            text="BOOK RECOMMENDER SYSTEM",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg="#1a1a1a",
        )
        title.pack(pady=10)

        main = tk.Frame(self.root, bg="#1a1a1a")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # LEFT: Users + Buttons
        left = tk.Frame(main, bg="#222222", bd=2, relief="ridge")
        left.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left, text="Users", font=("Segoe UI", 14, "bold"), fg="white", bg="#222222").pack(pady=5)

        self.user_list = tk.Listbox(
            left,
            width=28,
            height=18,
            font=("Segoe UI", 12),
            bg="#333333",
            fg="white",
            selectbackground="#00b4d8",
            bd=0,
            highlightthickness=0,
        )
        self.user_list.pack(padx=10, pady=5)

        for uid, user in sorted(self.users.items()):
            self.user_list.insert("end", f"{uid}: {user.name}")

        btn_frame = tk.Frame(left, bg="#222222")
        btn_frame.pack(padx=10, pady=10, fill="x")

        btn_style = {
            "font": ("Segoe UI", 11, "bold"),
            "fg": "white",
            "bg": "#00b4d8",
            "activebackground": "#0096c7",
            "bd": 0,
            "height": 2,
        }

        def add_btn(text, cmd):
            b = tk.Button(btn_frame, text=text, command=cmd, **btn_style)
            b.pack(fill="x", pady=3)
            return b

        add_btn("SHOW PURCHASES", self.show_purchases)
        add_btn("RECOMMEND BOOKS", self.show_recommendations)
        add_btn("SAVE TO JSON", self.save_data_clicked)
        add_btn("USER → BOOK GRAPH", self.show_graph)
        add_btn("SET OPERATIONS", self.show_sets)
        add_btn("JACCARD SIMILARITY", self.show_similarity)
        add_btn("CF LOGIC", self.show_cf_logic)
        add_btn("NETWORK GRAPH", self.show_network_graph)

        # RIGHT: Output
        right = tk.Frame(main, bg="#222222", bd=2, relief="ridge")
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="Output", font=("Segoe UI", 14, "bold"), fg="white", bg="#222222").pack(pady=5)

        self.output = tk.Text(
            right,
            bg="#333333",
            fg="white",
            font=("Consolas", 11),
            insertbackground="white",
        )
        self.output.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # EDITING AREA (bottom)
        edit = tk.Frame(self.root, bg="#1a1a1a")
        edit.pack(fill="x", padx=10, pady=5)

        # Add / edit user
        user_edit = tk.LabelFrame(
            edit,
            text="Add / Edit User",
            fg="white",
            bg="#1a1a1a",
            font=("Segoe UI", 11, "bold"),
            labelanchor="n",
        )
        user_edit.pack(side="left", fill="x", expand=True, padx=5)

        tk.Label(user_edit, text="User ID:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=3, pady=2
        )
        tk.Label(user_edit, text="Name:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="e", padx=3, pady=2
        )

        self.entry_user_id = tk.Entry(user_edit, font=("Segoe UI", 10), width=15)
        self.entry_user_name = tk.Entry(user_edit, font=("Segoe UI", 10), width=20)
        self.entry_user_id.grid(row=0, column=1, padx=3, pady=2)
        self.entry_user_name.grid(row=1, column=1, padx=3, pady=2)

        tk.Button(
            user_edit,
            text="Add / Update User",
            command=self.add_update_user,
            font=("Segoe UI", 10, "bold"),
            bg="#00b4d8",
            fg="white",
            bd=0,
        ).grid(row=0, column=2, rowspan=2, padx=5, pady=2, sticky="ns")

        # Add / edit book
        book_edit = tk.LabelFrame(
            edit,
            text="Add / Edit Book",
            fg="white",
            bg="#1a1a1a",
            font=("Segoe UI", 11, "bold"),
            labelanchor="n",
        )
        book_edit.pack(side="left", fill="x", expand=True, padx=5)

        tk.Label(book_edit, text="Book ID:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=3, pady=2
        )
        tk.Label(book_edit, text="Title:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="e", padx=3, pady=2
        )
        tk.Label(book_edit, text="Genre:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="e", padx=3, pady=2
        )

        self.entry_book_id = tk.Entry(book_edit, font=("Segoe UI", 10), width=10)
        self.entry_book_title = tk.Entry(book_edit, font=("Segoe UI", 10), width=18)
        self.entry_book_genre = tk.Entry(book_edit, font=("Segoe UI", 10), width=12)
        self.entry_book_id.grid(row=0, column=1, padx=3, pady=2)
        self.entry_book_title.grid(row=1, column=1, padx=3, pady=2)
        self.entry_book_genre.grid(row=2, column=1, padx=3, pady=2)

        tk.Button(
            book_edit,
            text="Add / Update Book",
            command=self.add_update_book,
            font=("Segoe UI", 10, "bold"),
            bg="#00b4d8",
            fg="white",
            bd=0,
        ).grid(row=0, column=2, rowspan=3, padx=5, pady=2, sticky="ns")

        # Purchase edit
        purchase_edit = tk.LabelFrame(
            edit,
            text="Edit Purchases for Selected User",
            fg="white",
            bg="#1a1a1a",
            font=("Segoe UI", 11, "bold"),
            labelanchor="n",
        )
        purchase_edit.pack(side="left", fill="x", expand=True, padx=5)

        tk.Label(purchase_edit, text="Add Book ID:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=3, pady=2
        )
        self.entry_purchase_book_id = tk.Entry(purchase_edit, font=("Segoe UI", 10), width=10)
        self.entry_purchase_book_id.grid(row=0, column=1, padx=3, pady=2)

        tk.Button(
            purchase_edit,
            text="Add Purchase",
            command=self.add_purchase,
            font=("Segoe UI", 10, "bold"),
            bg="#00b4d8",
            fg="white",
            bd=0,
        ).grid(row=0, column=2, padx=5, pady=2)

        tk.Label(purchase_edit, text="User's Books:", fg="white", bg="#1a1a1a", font=("Segoe UI", 10)).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=3
        )

        self.user_books_list = tk.Listbox(
            purchase_edit,
            height=4,
            font=("Segoe UI", 10),
            bg="#333333",
            fg="white",
            selectbackground="#00b4d8",
            bd=0,
            highlightthickness=0,
            width=30,
        )
        self.user_books_list.grid(row=2, column=0, columnspan=2, padx=3, pady=3, sticky="w")

        tk.Button(
            purchase_edit,
            text="Remove Selected",
            command=self.remove_purchase,
            font=("Segoe UI", 10, "bold"),
            bg="#e63946",
            fg="white",
            bd=0,
        ).grid(row=2, column=2, padx=5, pady=3)

        # When user selection changes, refresh user's book list
        self.user_list.bind("<<ListboxSelect>>", lambda e: self.refresh_user_books_list())

        # Bottom status bar
        bottom = tk.Frame(self.root, bg="#1a1a1a")
        bottom.pack(fill="x", padx=10, pady=(0, 5))
        tk.Label(
            bottom,
            text="Time complexity: " + self.rec.time_complexity_string(),
            font=("Segoe UI", 10),
            fg="white",
            bg="#1a1a1a",
        ).pack(side="left")

    #  HELPERS

    def get_selected_user_id(self) -> Optional[str]:
        try:
            idx = self.user_list.curselection()
            if not idx:
                return None
            item = self.user_list.get(idx[0])
            return item.split(":", 1)[0].strip()
        except Exception:
            return None

    def set_output(self, text: str) -> None:
        self.output.delete("1.0", "end")
        self.output.insert("end", text)

    def refresh_user_listbox(self):
        self.user_list.delete(0, "end")
        for uid, user in sorted(self.users.items()):
            self.user_list.insert("end", f"{uid}: {user.name}")
        self.refresh_user_books_list()

    def refresh_user_books_list(self):
        self.user_books_list.delete(0, "end")
        uid = self.get_selected_user_id()
        if not uid:
            return
        user = self.users.get(uid)
        if not user:
            return
        for bid in sorted(user.purchased_books):
            book = self.books.get(bid)
            if book:
                self.user_books_list.insert("end", f"{bid}: {book.title}")
            else:
                self.user_books_list.insert("end", f"{bid}: (Unknown)")

    #  CORE ACTIONS

    def show_purchases(self):
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Please select a user.")
            return
        user = self.users.get(uid)
        if not user:
            messagebox.showerror("Error", "User not found in data.")
            return
        lines = [f"User: {user.name} ({user.user_id})", "", "Purchased books:"]
        if not user.purchased_books:
            lines.append("  (none)")
        else:
            for bid in sorted(user.purchased_books):
                book = self.books.get(bid)
                if book:
                    lines.append(f"  - {book.title} [{book.genre}] (id={book.book_id})")
                else:
                    lines.append(f"  - Unknown book (id={bid})")
        self.set_output("\n".join(lines))

    def show_recommendations(self):
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Please select a user.")
            return
        try:
            recs = self.rec.recommend_books(uid)
        except KeyError:
            messagebox.showerror("Error", "Internal data error while recommending.")
            return
        lines = [f"Recommendations for {self.users[uid].name} ({uid})", "", "Recommended books:"]
        if not recs:
            lines.append("  (no recommendations available; maybe no similar users)")
        else:
            for book, score in recs:
                lines.append(f"  - {book.title} [{book.genre}]  score={score:.3f}")
        self.set_output("\n".join(lines))

    def save_data_clicked(self):
        try:
            save_all(self.users, self.books)
            messagebox.showinfo("Saved", "Data saved to users.json and books.json.")
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save data:\n{e}")

    #  CF / GRAPH / SET / SIMILARITY VIEWS 

    def show_graph(self):
        """Show dictionary mapping: user_id -> purchased_books set."""
        lines = ["USER → BOOK RELATIONSHIPS (dictionary mapping)", ""]
        for uid, user in self.users.items():
            lines.append(f"{uid}: {sorted(list(user.purchased_books))}")
        self.set_output("\n".join(lines))

    def show_sets(self):
        """Show set operations between selected user and others."""
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Select a user first.")
            return
        user = self.users[uid]
        lines = [f"Set operations for {user.name} ({uid})", ""]
        for other_id, other in self.users.items():
            if other_id == uid:
                continue
            inter = user.purchased_books & other.purchased_books
            union = user.purchased_books | other.purchased_books
            diff = user.purchased_books - other.purchased_books
            lines.append(f"Compared with {other.name} ({other_id}):")
            lines.append(f"  ∩ (intersection, common books): {sorted(list(inter))}")
            lines.append(f"  ∪ (union, all distinct books): {sorted(list(union))}")
            lines.append(f"  − (books only {user.name} has): {sorted(list(diff))}")
            lines.append("")
        self.set_output("\n".join(lines))

    def show_similarity(self):
        """Show Jaccard similarity between selected user and all others."""
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Select a user first.")
            return
        lines = [f"Jaccard similarity for {uid} vs. other users", ""]
        for other_id, other in self.users.items():
            if other_id == uid:
                continue
            sim = self.rec.jaccard_similarity(self.users[uid].purchased_books, other.purchased_books)
            lines.append(f"{uid} ↔ {other_id}: {sim:.3f}")
        self.set_output("\n".join(lines))

    def show_cf_logic(self):
        """Explain the collaborative filtering steps for the selected user."""
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Select a user first.")
            return
        user = self.users[uid]
        lines = [f"Collaborative filtering explanation for {user.name} ({uid})", ""]
        lines.append("1) Compute Jaccard similarity with all other users:")
        sims = self.rec.most_similar_users(uid, top_k=len(self.users) - 1)
        for other, sim in sims:
            lines.append(f"   - {other.user_id} ({other.name}): similarity={sim:.3f}")
        lines.append("")
        lines.append("2) Collect books from similar users that this user hasn't bought,")
        lines.append("   and weight them by similarity score.")
        score_map: Dict[str, float] = {}
        for other, sim in sims:
            for bid in other.purchased_books:
                if bid in user.purchased_books:
                    continue
                score_map[bid] = score_map.get(bid, 0.0) + sim
        if not score_map:
            lines.append("   No extra books found from similar users.")
        else:
            for bid, score in sorted(score_map.items(), key=lambda x: x[1], reverse=True):
                book = self.books.get(bid)
                if book:
                    lines.append(f"   - {book.title} (id={bid}) score={score:.3f}")
                else:
                    lines.append(f"   - Unknown book id={bid}, score={score:.3f}")
        lines.append("")
        lines.append("3) Recommend the highest scoring books (see 'RECOMMEND BOOKS' button).")
        self.set_output("\n".join(lines))

    def show_network_graph(self):
        """
        Graphical network visualization:
        - Blue circles: users
        - Yellow squares: books
        - Lines: purchases (edges)
        """
        if not self.users or not self.books:
            messagebox.showinfo("No data", "No users or books to display.")
            return

        top = tk.Toplevel(self.root)
        top.title("User–Book Network Graph")

        canvas_width = 800
        canvas_height = 500
        cv = tk.Canvas(top, width=canvas_width, height=canvas_height, bg="#1a1a1a", highlightthickness=0)
        cv.pack(fill="both", expand=True)

        user_x = canvas_width * 0.25
        book_x = canvas_width * 0.75
        user_y_step = canvas_height / (len(self.users) + 1)
        book_y_step = canvas_height / (len(self.books) + 1)

        user_pos: Dict[str, Tuple[float, float]] = {}
        book_pos: Dict[str, Tuple[float, float]] = {}

        r = 18

        # Draw user nodes
        for idx, (uid, user) in enumerate(sorted(self.users.items()), start=1):
            y = user_y_step * idx
            user_pos[uid] = (user_x, y)
            cv.create_oval(user_x - r, y - r, user_x + r, y + r, fill="#00b4d8", outline="#eeeeee")
            cv.create_text(user_x, y - 28, text=uid, fill="white", font=("Segoe UI", 9, "bold"))
            cv.create_text(user_x, y + 28, text=user.name, fill="#dddddd", font=("Segoe UI", 8))

        # Draw book nodes
        for idx, (bid, book) in enumerate(sorted(self.books.items()), start=1):
            y = book_y_step * idx
            book_pos[bid] = (book_x, y)
            cv.create_rectangle(book_x - r, y - r, book_x + r, y + r, fill="#ffd166", outline="#333333")
            cv.create_text(book_x, y - 28, text=bid, fill="white", font=("Segoe UI", 9, "bold"))
            cv.create_text(book_x, y + 28, text=book.title, fill="#dddddd", font=("Segoe UI", 8), width=160)

        # Draw edges (purchases)
        for uid, user in self.users.items():
            ux, uy = user_pos[uid]
            for bid in user.purchased_books:
                if bid in book_pos:
                    bx, by = book_pos[bid]
                    cv.create_line(ux + r, uy, bx - r, by, fill="#aaaaaa")

        info = tk.Label(
            top,
            text="Blue circles = Users, Yellow squares = Books, Lines = Purchases",
            fg="white",
            bg="#1a1a1a",
            font=("Segoe UI", 10),
        )
        info.pack(pady=4)

    #EDITING ACTIONS

    def add_update_user(self):
        uid = self.entry_user_id.get().strip()
        name = self.entry_user_name.get().strip()
        if not uid or not name:
            messagebox.showwarning("Missing data", "Please enter both User ID and Name.")
            return
        if uid in self.users:
            self.users[uid].name = name
            messagebox.showinfo("Updated", f"Updated user {uid}.")
        else:
            self.users[uid] = User(user_id=uid, name=name, purchased_books=set())
            messagebox.showinfo("Added", f"Added new user {uid}.")
        self.refresh_user_listbox()

    def add_update_book(self):
        bid = self.entry_book_id.get().strip()
        title = self.entry_book_title.get().strip()
        genre = self.entry_book_genre.get().strip() or "Unknown"
        if not bid or not title:
            messagebox.showwarning("Missing data", "Please enter at least Book ID and Title.")
            return
        if bid in self.books:
            b = self.books[bid]
            b.title = title
            b.genre = genre
            messagebox.showinfo("Updated", f"Updated book {bid}.")
        else:
            self.books[bid] = Book(book_id=bid, title=title, genre=genre)
            messagebox.showinfo("Added", f"Added new book {bid}.")
        self.refresh_user_books_list()

    def add_purchase(self):
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Select a user first.")
            return
        bid = self.entry_purchase_book_id.get().strip()
        if not bid:
            messagebox.showwarning("No book ID", "Enter a Book ID to add.")
            return
        if bid not in self.books:
            messagebox.showerror("Invalid book", "Book ID not found; add the book first in 'Add / Edit Book'.")
            return
        user = self.users[uid]
        if bid in user.purchased_books:
            messagebox.showinfo("Already there", f"User already has book {bid}.")
            return
        user.purchased_books.add(bid)
        self.refresh_user_books_list()
        messagebox.showinfo("Added", "Book added to user's purchases.")

    def remove_purchase(self):
        uid = self.get_selected_user_id()
        if not uid:
            messagebox.showwarning("No user", "Select a user first.")
            return
        sel = self.user_books_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Select a book from the user's list.")
            return
        item = self.user_books_list.get(sel[0])
        bid = item.split(":", 1)[0].strip()
        user = self.users[uid]
        if bid in user.purchased_books:
            user.purchased_books.remove(bid)
            self.refresh_user_books_list()
            messagebox.showinfo("Removed", "Book removed from user's purchases.")
        else:
            messagebox.showerror("Error", "Book not found in user's purchases.")



# Run the app


def main():
    users, books, msg = load_data()
    rec = RecommenderSystem(users, books)
    root = tk.Tk()
    app = BookstoreGUI(root, rec, users, books)
    if msg:
        messagebox.showinfo("Data notice", msg)
    root.mainloop()


if __name__ == "__main__":
    main()
