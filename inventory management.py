import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
import random

INVENTORY_FILE = "coursework/inventory managment/inventory.json"
ORDER_FILE = "coursework/inventory managment/orders.json"

# Inventory Item

class InventoryItem:
    def __init__(self, item_id, name, quantity, threshold, reorder_amount, group, supplier_id):
        self.id = item_id
        self.name = name
        self.quantity = quantity
        self.threshold = threshold
        self.reorder_amount = reorder_amount
        self.group = group
        self.supplier_id = supplier_id
        self.last_reordered = None

    def needs_reorder(self):
        return self.quantity < self.threshold

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "threshold": self.threshold,
            "reorder_amount": self.reorder_amount,
            "group": self.group,
            "supplier_id": self.supplier_id,
            "last_reordered": self.last_reordered
        }


# Inventory Manager
class InventoryManager:
    def __init__(self):
        self.items = {}
        self.load_data()

    # JSON LOAD 
    def load_data(self):
        try:
            with open(INVENTORY_FILE, "r") as f:
                data = json.load(f)
            for item_id, d in data.items():
                item = InventoryItem(
                    d["id"], d["name"], d["quantity"], d["threshold"],
                    d["reorder_amount"], d["group"], d["supplier_id"]
                )
                item.last_reordered = d["last_reordered"]
                self.items[item_id] = item
        except FileNotFoundError:
            pass

    #  SAVE
    def save_data(self):
        data = {i: item.to_dict() for i, item in self.items.items()}
        with open(INVENTORY_FILE, "w") as f:
            json.dump(data, f, indent=4)

    #  CRUD 
    def add_item(self, item):
        if item.id in self.items:
            return False
        self.items[item.id] = item
        self.save_data()
        return True

    def update_item(self, item_id, name, quantity, threshold, reorder_amount, group):
        if item_id not in self.items:
            return False

        item = self.items[item_id]
        item.name = name
        item.quantity = quantity
        item.threshold = threshold
        item.reorder_amount = reorder_amount
        item.group = group

        self.save_data()
        return True

    def delete_item(self, item_id):
        # delete by matching the InventoryItem.id field, not assuming dict key
        key_to_delete = None
        for key, item in self.items.items():
            if str(item.id).strip() == str(item_id).strip():
                key_to_delete = key
                break

        if key_to_delete is not None:
            del self.items[key_to_delete]
            self.save_data()
            return True

        return False

    #  STOCK UPDATE 
    def set_quantity(self, item_id, new_quantity):
        # find the actual item object by matching its .id field
        target = None
        for item in self.items.values():
            if str(item.id).strip() == str(item_id).strip():
                target = item
                break

        if target is None:
            return False

        try:
            q = int(str(new_quantity).strip())
        except ValueError:
            return False
        if q < 0:
            return False

        target.quantity = q
        self.save_data()
        return True

    #  SEARCH
    def search(self, field, text):
        text = text.lower()
        results = []

        for item in self.items.values():
            value = str(getattr(item, field)).lower()
            if text in value:
                results.append(item)

        return results

    #  SORT 
    def sort_by_group(self):
        return sorted(self.items.values(), key=lambda x: x.group)



# Order Manager

class OrderManager:
    def __init__(self):
        self.orders = []
        self.load_orders()

    def load_orders(self):
        try:
            with open(ORDER_FILE, "r") as f:
                self.orders = json.load(f)
        except FileNotFoundError:
            pass

    def save_orders(self):
        with open(ORDER_FILE, "w") as f:
            json.dump(self.orders, f, indent=4)

    def create_order(self, item_id, item_name, quantity, supplier_id):
        order = {
            "order_id": f"ORD{random.randint(1000,9999)}",
            "item_id": item_id,
            "item_name": item_name,
            "quantity": quantity,
            "supplier_id": supplier_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.orders.append(order)
        self.save_orders()
        return order


# Add Item Window

class AddItemWindow:
    def __init__(self, parent, manager, refresh_callback):
        self.manager = manager
        self.refresh_callback = refresh_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Add New Item")
        self.win.geometry("400x450")

        groups = ["Electronics", "Grocery", "Clothing", "Stationery", "Others"]

        fields = ["Item ID", "Name", "Quantity", "Threshold", "Reorder Amount"]
        self.entries = {}

        for i, label in enumerate(fields):
            ttk.Label(self.win, text=label).pack()
            entry = ttk.Entry(self.win, width=30)
            entry.pack(pady=3)
            self.entries[label] = entry

        ttk.Label(self.win, text="Group").pack()
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(self.win, textvariable=self.group_var, values=groups, state="readonly")
        self.group_combo.pack()

        # Supplier auto generate
        self.supplier_id = f"SUP{random.randint(1000,9999)}"

        ttk.Button(self.win, text="Add Item", command=self.save_item).pack(pady=10)

    def save_item(self):
        try:
            item = InventoryItem(
                self.entries["Item ID"].get(),
                self.entries["Name"].get(),
                int(self.entries["Quantity"].get()),
                int(self.entries["Threshold"].get()),
                int(self.entries["Reorder Amount"].get()),
                self.group_var.get(),
                self.supplier_id
            )
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric input")
            return

        if not self.manager.add_item(item):
            messagebox.showerror("Error", "Item ID already exists!")
            return

        messagebox.showinfo("Success", "Item added successfully.")
        self.refresh_callback()
        self.win.destroy()


# Order Window

class OrderWindow:
    def __init__(self, parent, manager, order_manager, refresh_callback):
        self.manager = manager
        self.order_manager = order_manager
        self.refresh_callback = refresh_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Order Item")
        self.win.geometry("400x300")

        ttk.Label(self.win, text="Select Item").pack()
        self.item_var = tk.StringVar()
        item_list = [f"{i.id} - {i.name}" for i in manager.items.values()]
        self.item_combo = ttk.Combobox(self.win, values=item_list, textvariable=self.item_var, state="readonly")
        self.item_combo.pack()

        ttk.Label(self.win, text="Quantity").pack()
        self.qty_entry = ttk.Entry(self.win)
        self.qty_entry.pack()

        ttk.Button(self.win, text="Place Order", command=self.place_order).pack(pady=10)

    def place_order(self):
        if not self.item_var.get():
            messagebox.showerror("Error", "Select an item")
            return

        item_id = self.item_var.get().split(" - ")[0]
        item = self.manager.items[item_id]

        try:
            qty = int(self.qty_entry.get())
        except:
            messagebox.showerror("Error", "Invalid quantity")
            return

        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive")
            return

        # create order record
        order = self.order_manager.create_order(item_id, item.name, qty, item.supplier_id)

        # update stock: receiving an order increases on-hand quantity
        item.quantity += qty
        self.manager.save_data()

        messagebox.showinfo("Order Placed", f"Order ID: {order['order_id']}\nStock updated by +{qty}.")
        # refresh main table and threshold highlighting
        if self.refresh_callback:
            self.refresh_callback()
        self.win.destroy()

# Update Stock Window

class UpdateStockWindow:
    def __init__(self, parent, manager, refresh_callback):
        self.manager = manager
        self.refresh_callback = refresh_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Update Stock")
        self.win.geometry("500x400")

        header = ttk.Label(self.win, text="Update Stock Levels", font=("Segoe UI", 12, "bold"))
        header.pack(pady=5)

        frame = ttk.Frame(self.win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # include a NEW_QTY column to hold the new stock quantity
        cols = ("id", "name", "quantity", "new_qty")
        self.table = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.table.heading(c, text=c.upper())
            self.table.column(c, width=120)
        self.table.pack(fill="both", expand=True)

        for item in self.manager.items.values():
            # last column (NEW_QTY) starts empty until user enters a value
            self.table.insert("", tk.END, values=(item.id, item.name, item.quantity, ""))

        bottom = ttk.Frame(self.win)
        bottom.pack(fill="x", padx=10, pady=10)

        ttk.Button(bottom, text="Apply Selected Row", command=self.apply_update).pack(side="left", padx=5)

        # support in-place editing of NEW_QTY cells
        self.table.bind("<Double-1>", self.start_edit_cell)
        self.edit_entry = None

    def start_edit_cell(self, event):
        # detect which row/column was clicked
        region = self.table.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.table.identify_row(event.y)
        col_id = self.table.identify_column(event.x)

        # only allow editing of NEW_QTY column (#4)
        if col_id != "#4" or not row_id:
            return

        # get cell bounding box
        x, y, w, h = self.table.bbox(row_id, col_id)
        value = self.table.set(row_id, "new_qty")

        # destroy previous editor if any
        if self.edit_entry is not None:
            self.edit_entry.destroy()

        self.edit_entry = tk.Entry(self.table)
        self.edit_entry.place(x=x, y=y, width=w, height=h)
        self.edit_entry.insert(0, value)
        self.edit_entry.focus()

        # save on Enter or focus out
        self.edit_entry.bind("<Return>", lambda e, r=row_id: self.finish_edit_cell(r))
        self.edit_entry.bind("<FocusOut>", lambda e, r=row_id: self.finish_edit_cell(r))

    def finish_edit_cell(self, row_id):
        if self.edit_entry is None:
            return
        new_val = self.edit_entry.get().strip()
        self.edit_entry.destroy()
        self.edit_entry = None

        # write new value into NEW_QTY column for that row
        vals = list(self.table.item(row_id)["values"])
        if len(vals) < 4:
            return
        vals[3] = new_val
        self.table.item(row_id, values=vals)

    def apply_update(self):
        selected = self.table.focus()
        if not selected:
            messagebox.showerror("Error", "Select a product to update")
            return

        vals = list(self.table.item(selected)["values"])
        item_id = vals[0]
        # prefer NEW_QTY cell; if empty, fall back to current quantity
        new_q = str(vals[3]).strip() or str(vals[2]).strip()

        if not self.manager.set_quantity(item_id, new_q):
            messagebox.showerror("Error", "Please enter a valid non-negative number")
            return

        messagebox.showinfo("Updated", "Stock level updated")

        # write the new quantity back into the QUANTITY and NEW_QTY columns
        vals[2] = int(new_q)
        vals[3] = new_q
        self.table.item(selected, values=vals)

        # refresh main table and check thresholds in the main GUI
        self.refresh_callback()



# Main GUI

class InventoryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory System")
        self.root.geometry("1300x600")
        self.root.configure(bg="#00151c")  # darker blue background

        self.manager = InventoryManager()
        self.order_manager = OrderManager()

        self.build_ui()
        self.load_table()
        self.check_all_thresholds()

    def build_ui(self):
        main = tk.Frame(self.root, bg="#00151c")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Search Section
        # Left button panel
        button_frame = tk.Frame(main, bg="#00151c")
        button_frame.pack(side="left", fill="y", padx=(0, 20))

        # Top search section
        search_frame = tk.Frame(main, bg="#00151c")
        search_frame.pack(fill="x", pady=5)

        tk.Label(search_frame, text="Search by: ", fg="white", bg="#00151c", font=("Segoe UI", 11, "bold")).pack(side="left")

        self.search_field = tk.StringVar()
        search_fields = ["id", "name", "group", "supplier_id"]
        self.search_combo = ttk.Combobox(search_frame, textvariable=self.search_field, values=search_fields, width=15)
        self.search_combo.current(0)
        self.search_combo.pack(side="left")

        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.perform_search)

        ttk.Button(search_frame, text="Sort by Group", command=self.sort_group).pack(side="left", padx=5)

        # Buttons 
        btn_style = ttk.Style()
        btn_style.theme_use("clam")

        btn_style.configure("Green.TButton", font=("Segoe UI", 13, "bold"), padding=20,
                    foreground="white", background="#006400")
        btn_style.map("Green.TButton", background=[("active", "#008000")])

        btn_style.configure("Blue.TButton", font=("Segoe UI", 13, "bold"), padding=20,
                    foreground="white", background="#003366")
        btn_style.map("Blue.TButton", background=[("active", "#004c99")])

        btn_style.configure("Red.TButton", font=("Segoe UI", 13, "bold"), padding=20,
                    foreground="white", background="#660000")
        btn_style.map("Red.TButton", background=[("active", "#990000")])

        ttk.Button(button_frame, text="Add Item", command=self.open_add_window, style="Green.TButton").pack(fill="x", pady=10)
        ttk.Button(button_frame, text="Order Item", command=self.open_order_window, style="Blue.TButton").pack(fill="x", pady=10)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected, style="Red.TButton").pack(fill="x", pady=10)
        ttk.Button(button_frame, text="Update Stock", command=self.open_update_window, style="Green.TButton").pack(fill="x", pady=10)

        # Table 
        columns = ("id", "name", "quantity", "threshold", "reorder", "group", "supplier", "last_reordered")
        self.table = ttk.Treeview(main, columns=columns, show="headings", height=20)

        for col in columns:
            self.table.heading(col, text=col.upper())
            self.table.column(col, width=140)

        self.table.pack(fill="both", expand=True)


    def load_table(self, items=None):
        for row in self.table.get_children():
            self.table.delete(row)

        if items is None:
            items = self.manager.items.values()

        for item in items:
            self.table.insert("", tk.END, values=(
                item.id, item.name, item.quantity, item.threshold,
                item.reorder_amount, item.group, item.supplier_id,
                item.last_reordered
            ))

        # after loading, highlight low-stock rows
        self.highlight_low_stock_rows()

    def highlight_low_stock_rows(self):
        # configure tag
        self.table.tag_configure("low_stock", background="#5c1b1b", foreground="white")

        for row in self.table.get_children():
            vals = self.table.item(row)["values"]
            if len(vals) < 4:
                continue
            qty = vals[2]
            thr = vals[3]
            try:
                qty = int(qty)
                thr = int(thr)
            except ValueError:
                continue
            if qty <= thr:
                self.table.item(row, tags=("low_stock",))
            else:
                self.table.item(row, tags=("",))

    def check_all_thresholds(self):
        # if any item is at or below threshold, show a single alert
        low_items = [item for item in self.manager.items.values() if item.needs_reorder()]
        if low_items:
            names = ", ".join(f"{i.name} (qty {i.quantity}, thr {i.threshold})" for i in low_items)
            messagebox.showwarning("Low Stock Alert", f"The following items are at or below threshold:\n{names}")

    def perform_search(self, event=None):
        field = self.search_field.get()
        text = self.search_entry.get()

        if text == "":
            self.load_table()
            return

        results = self.manager.search(field, text)
        self.load_table(results)

    def sort_group(self):
        sorted_items = self.manager.sort_by_group()
        self.load_table(sorted_items)

 
    def open_add_window(self):
        AddItemWindow(self.root, self.manager, self.load_table)

    def open_order_window(self):
        OrderWindow(self.root, self.manager, self.order_manager, self.after_order)

    def after_order(self):
        # reload table and re-check thresholds after an order updates stock
        self.load_table()
        self.check_all_thresholds()

    def open_update_window(self):
        UpdateStockWindow(self.root, self.manager, self.load_table)


    def delete_selected(self):
        # use selection() instead of focus() to get the clicked row
        selected_items = self.table.selection()
        if not selected_items:
            messagebox.showerror("Error", "Select an item to delete")
            return

        # for now, delete only the first selected row
        row_id = selected_items[0]
        values = self.table.item(row_id)["values"]
        if not values:
            messagebox.showerror("Error", "Could not read selected item")
            return

        item_id = values[0]

        # optional confirmation
        if not messagebox.askyesno("Confirm Delete", f"Delete item '{item_id}'?"):
            return

        if self.manager.delete_item(item_id):
            messagebox.showinfo("Deleted", "Item deleted")
            self.load_table()
            self.check_all_thresholds()



# Run App

if __name__ == "__main__":
    root = tk.Tk()
    InventoryGUI(root)
    root.mainloop()
