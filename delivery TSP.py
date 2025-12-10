import tkinter as tk
from tkinter import ttk, messagebox
import requests
import math
import webbrowser
import threading
from itertools import permutations
import json
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from io import BytesIO


#  Geocoding + Distance (Its use two apps to get the geocode data some time google geocode api fails so its use street map)

def geocode_postcode(query, api_key=None):
    """Return (lat, lon, formatted_address, debug) for the query."""
    debug = {"query": query, "provider": "google" if api_key else "nominatim"}

    if api_key:
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": query, "key": api_key}
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            debug["response"] = data
            debug["http_status"] = r.status_code

            if data.get("status") == "OK" and data.get("results"):
                res = data["results"][0]
                loc = res["geometry"]["location"]
                return float(loc["lat"]), float(loc["lng"]), res.get("formatted_address", query), debug

            debug["error"] = data.get("status")
            return None, debug

        except Exception as e:
            debug["error"] = str(e)
            return None, debug


    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 1}
        headers = {"User-Agent": "DeliveryRouteOptimizer/1.0"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        debug["http_status"] = r.status_code
        debug["response"] = data

        if r.status_code == 200 and data:
            res = data[0]
            return float(res["lat"]), float(res["lon"]), res.get("display_name", query), debug

        debug["error"] = "no_results"
        return None, debug

    except Exception as e:
        debug["error"] = str(e)
        return None, debug


def haversine(a, b):
    """Return distance in KM between (lat, lon) points."""
    R = 6371
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


#  Algorithm Classes

class NearestNeighbourAlgorithm:
    """Compute nearest neighbour order and distance."""
    def compute(self, start, points):
        unvisited = list(range(len(points)))
        current = start
        order = []
        total = 0

        while unvisited:
            best = None
            best_d = 10**9
            for i in unvisited:
                d = haversine(current, (points[i][0], points[i][1]))
                if d < best_d:
                    best_d = d
                    best = i
            order.append(best)
            total += best_d
            current = (points[best][0], points[best][1])
            unvisited.remove(best)

        total += haversine(current, start)
        return order, total


class BruteForceAlgorithm:
    """Compute brute-force TSP solution."""
    def compute(self, start, points):
        best_order = None
        best_distance = 10**9

        for perm in permutations(range(len(points))):
            current = start
            total = 0
            for i in perm:
                p = (points[i][0], points[i][1])
                total += haversine(current, p)
                current = p
            total += haversine(current, start)

            if total < best_distance:
                best_distance = total
                best_order = perm

        return list(best_order), best_distance


class Geocoder:
    def __init__(self, api_key):
        self.api_key = api_key

    def geocode(self, q):
        return geocode_postcode(q, self.api_key)


class MapPreview:
    def __init__(self, pil_available):
        self.pil_available = pil_available

    def generate(self, start, points):
        if not self.pil_available:
            return None

        base = "https://staticmap.openstreetmap.de/staticmap.php"
        markers = [f"{start[0]},{start[1]},red"]
        markers += [f"{p[0]},{p[1]},blue" for p in points]

        params = {
            "center": f"{start[0]},{start[1]}",
            "zoom": "12",
            "size": "600x300",
            "markers": "|".join(markers)
        }

        try:
            r = requests.get(base, params=params, timeout=10)
            r.raise_for_status()
            return Image.open(BytesIO(r.content))
        except:
            return None


class GraphDrawer:
    """Draw a geographic-style graph: nodes placed by lat/lon, edges as arrows with distances."""
    def draw(self, canvas, labels, coords, edges, highlight=True):
        canvas.delete("all")
        if not labels or not coords or len(labels) != len(coords):
            return

        # compute bounds
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        w = int(canvas["width"])
        h = int(canvas["height"])
        margin = 30

        # avoid division by zero if all lats/lons are same
        lat_span = max(max_lat - min_lat, 1e-9)
        lon_span = max(max_lon - min_lon, 1e-9)

        def to_canvas(lat, lon):    
            x = margin + (lon - min_lon) / lon_span * (w - 2 * margin)
            # invert lat so north is up
            y = margin + (max_lat - lat) / lat_span * (h - 2 * margin)
            return x, y

        positions = {}
        for i, (label, (lat, lon)) in enumerate(zip(labels, coords)):
            x, y = to_canvas(lat, lon)
            positions[i] = (x, y)
            canvas.create_oval(x-15, y-15, x+15, y+15,
                               fill="#ff7043" if i == 0 else "#4aa3ff")
            canvas.create_text(x, y-22, text=label, fill="black")

        line_color = "#2e7d32" if highlight else "#999999"
        for (i, j, d) in edges:
            x1, y1 = positions[i]
            x2, y2 = positions[j]
            canvas.create_line(x1, y1, x2, y2, fill=line_color, width=2,
                               arrow=tk.LAST, arrowshape=(12, 15, 6))
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            canvas.create_text(mx, my, text=f"{d:.1f} km", fill="red")



#  GUI Application


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Road Smart Optimizer")
        self.geometry("1050x760")
        self.configure(bg="#e3f2fd")  # lighter blue background

        try:
            self.iconbitmap("app.ico")
        except:
            pass

        self.start_loc = None
        self.points = None
        self.order_nn = None
        self.order_bf = None
        self.map_img = None
        self.point_labels = None
        self.destinations_raw = []   # list of postcode strings
        self.labels_raw = []         # list of label strings (same length as destinations_raw)

        self.logo_img = None  # holder for logo image

        self.create_widgets()

    def create_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#e3f2fd")
        style.configure("TLabel", background="#e3f2fd", font=("Segoe UI", 11))
        style.configure("Header.TLabel", background="#e3f2fd", foreground="#0d47a1",
                        font=("Segoe UI", 22, "bold"))
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("!disabled", "#42a5f5"), ("pressed", "#1e88e5"), ("active", "#64b5f6")],
                  foreground=[("!disabled", "white")])
        style.configure("TLabelframe", background="#e3f2fd")
        style.configure("TLabelframe.Label", background="#e3f2fd", font=("Segoe UI", 11, "bold"))

        # top banner with logo + title
        top_banner = ttk.Frame(main)
        top_banner.pack(fill="x", pady=(0, 10))

        # optional logo on the left, if file exists and PIL is available
        if PIL_AVAILABLE and os.path.exists("logo.png"):
            try:
                raw_logo = Image.open("logo.png")
                raw_logo.thumbnail((80, 80))
                self.logo_img = ImageTk.PhotoImage(raw_logo)
                logo_lbl = ttk.Label(top_banner, image=self.logo_img)
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_container = ttk.Frame(top_banner)
        title_container.pack(side="left", expand=True)

        ttk.Label(title_container, text="Road Smart Optimizer", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_container,
                  text="Plan, visualize and optimize multi-stop road journeys",
                  foreground="#1565c0",
                  font=("Segoe UI", 10, "italic")).pack(anchor="w")

        # coloured separator
        sep = ttk.Separator(main, orient="horizontal")
        sep.pack(fill="x", pady=(0, 8))

        # --- Inputs Frame ---
        f_in = ttk.LabelFrame(main, text="Input", padding=10)
        f_in.pack(side="left", fill="y", padx=10, pady=10)

        # change labels slightly with colour accents
        ttk.Label(f_in, text="Google API Key (optional):",
                  foreground="#01579b").grid(row=0, column=0, sticky="w")
        self.api_entry = ttk.Entry(f_in, width=40)
        self.api_entry.grid(row=0, column=1, pady=3)

        ttk.Label(f_in, text="Start Postcode:",
                  foreground="#01579b").grid(row=1, column=0, sticky="w")
        self.start_entry = ttk.Entry(f_in, width=40)
        self.start_entry.grid(row=1, column=1, pady=3)

        ttk.Label(f_in, text="Location Postcode:",
                  foreground="#0277bd").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.loc_postcode_entry = ttk.Entry(f_in, width=40)
        self.loc_postcode_entry.grid(row=2, column=1, pady=(8, 0))

        ttk.Label(f_in, text="Location Label (optional):",
                  foreground="#0277bd").grid(row=3, column=0, sticky="w")
        self.loc_label_entry = ttk.Entry(f_in, width=40)
        self.loc_label_entry.grid(row=3, column=1, pady=3)

        self.add_loc_btn = ttk.Button(f_in, text="Add Location", command=self.add_location)
        self.add_loc_btn.grid(row=4, column=1, sticky="w", pady=(4, 8))

        ttk.Label(f_in, text="Locations:", foreground="#006064").grid(row=5, column=0, sticky="nw")
        self.locations_list = tk.Listbox(f_in, width=40, height=8,
                                         bg="#e1f5fe", fg="#01579b", selectbackground="#0288d1")
        self.locations_list.grid(row=5, column=1, pady=(0, 4))

        ttk.Button(f_in, text="Example", command=self.load_example).grid(row=6, column=0, pady=5)
        ttk.Button(f_in, text="Compute", command=self.thread_compute).grid(row=6, column=1, sticky="w")

        # --- Output Frame ---
        f_out = ttk.LabelFrame(main, text="Output", padding=10)
        f_out.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.out_box = tk.Text(f_out, width=60, height=20, bg="#fff3e0", fg="#4e342e")
        self.out_box.pack(fill="both", expand=True)

        # buttons row with a slightly tinted background
        btn_row = ttk.Frame(f_out)
        btn_row.pack(fill="x", pady=(6, 4))
        ttk.Button(btn_row, text="Open in Google Maps", command=self.open_maps).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Save Locations", command=self.save_locations).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Load Locations", command=self.load_locations).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Map Preview", command=self.show_map_preview).pack(side="left", padx=2)

        # --- Tabs ---
        self.tabs = ttk.Notebook(f_out)
        self.tabs.pack(fill="both", expand=True)

        # Nearest Neighbour Tab
        self.nn_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.nn_tab, text="Nearest Neighbour")
        self.nn_canvas = tk.Canvas(self.nn_tab, width=800, height=400, bg="#e8f5e9", highlightthickness=0)
        self.nn_canvas.pack()

        # Brute Force Tab
        self.bf_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.bf_tab, text="Brute Force (Optimal)")
        self.bf_canvas = tk.Canvas(self.bf_tab, width=800, height=400, bg="#f3e5f5", highlightthickness=0)
        self.bf_canvas.pack()



    def add_location(self):
        """Add a single location (postcode + optional label) to the form lists and listbox."""
        pc = self.loc_postcode_entry.get().strip()
        lbl = self.loc_label_entry.get().strip()
        if not pc:
            messagebox.showerror("Missing", "Please enter a location postcode")
            return
        if not lbl:
            lbl = f"Location {len(self.destinations_raw) + 1}"
        self.destinations_raw.append(pc)
        self.labels_raw.append(lbl)
        self.locations_list.insert("end", f"{lbl} ({pc})")
        self.loc_postcode_entry.delete(0, "end")
        self.loc_label_entry.delete(0, "end")

    def load_example(self):
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, "RM1 4AN")
        # Clear existing lists
        self.destinations_raw = []
        self.labels_raw = []
        self.locations_list.delete(0, "end")
        # Add example locations
        examples = [
            ("CM13 3ES", "Home"),
            ("RM1 3GL", "Office"),
            ("RM3 0AG", "Warehouse"),
        ]
        for pc, lbl in examples:
            self.destinations_raw.append(pc)
            self.labels_raw.append(lbl)
            self.locations_list.insert("end", f"{lbl} ({pc})")

  

    def thread_compute(self):
        threading.Thread(target=self.compute, daemon=True).start()


    def compute(self):
        api = self.api_entry.get().strip() or None
        start_q = self.start_entry.get().strip()
        dests = list(self.destinations_raw)
        raw_labels = list(self.labels_raw)

        if not start_q:
            messagebox.showerror("Missing", "Start address required")
            return
        if not dests:
            messagebox.showerror("Missing", "Need at least one destination")
            return

        geocoder = Geocoder(api)
        start_geo = geocoder.geocode(start_q)
        if not start_geo or start_geo[0] is None:
            messagebox.showerror("Error", "Failed geocoding start")
            return
        self.start_loc = (start_geo[0], start_geo[1])

        self.points = []
        for d in dests:
            g = geocoder.geocode(d)
            if not g or g[0] is None:
                messagebox.showerror("Error", f"Failed geocoding {d}")
                return
            self.points.append((g[0], g[1], g[2]))

        # After building self.points, build display labels per destination
        if raw_labels and len(raw_labels) == len(self.points):
            self.point_labels = raw_labels
        else:
            # Fallback: generate Location 1, 2, ...
            self.point_labels = [f"Location {i+1}" for i in range(len(self.points))]

        # Compute Nearest Neighbour
        nn = NearestNeighbourAlgorithm()
        self.order_nn, dist_nn = nn.compute(self.start_loc, self.points)

        # Compute Brute Force
        bf = BruteForceAlgorithm()
        self.order_bf, dist_bf = bf.compute(self.start_loc, self.points)

        # Print results
        self.out_box.delete("1.0", "end")
        self.out_box.insert("end", "Nearest Neighbour:\n")
        for idx in self.order_nn:
            self.out_box.insert("end", f" → {self.point_labels[idx]} ({self.points[idx][2]})\n")
        self.out_box.insert("end", f"Total: {dist_nn:.2f} km\n\n")

        self.out_box.insert("end", "Brute Force:\n")
        for idx in self.order_bf:
            self.out_box.insert("end", f" → {self.point_labels[idx]} ({self.points[idx][2]})\n")
        self.out_box.insert("end", f"Total: {dist_bf:.2f} km\n")

        # Draw graphs
        gd = GraphDrawer()
        labels = ["Start"] + self.point_labels
        coords = [self.start_loc] + [(p[0], p[1]) for p in self.points]
        # Build a helper to create edges between every consecutive node (including return)
        def build_edges(order):
            edges = []
            prev_idx = 0  # start index in labels
            prev_point = self.start_loc
            for pos, pt_idx in enumerate(order, start=1):
                pt = (self.points[pt_idx][0], self.points[pt_idx][1])
                d = haversine(prev_point, pt)
                edges.append((prev_idx, pos, d))
                prev_idx, prev_point = pos, pt
            # return to start
            d_back = haversine(prev_point, self.start_loc)
            edges.append((prev_idx, 0, d_back))
            return edges

        nn_edges = build_edges(self.order_nn)
        bf_edges = build_edges(self.order_bf)

        # NN graph: heuristic path with arrows and distances
        gd.draw(self.nn_canvas, labels, coords, nn_edges, highlight=True)
        # BF graph: optimal (shortest) path with arrows and distances
        gd.draw(self.bf_canvas, labels, coords, bf_edges, highlight=True)

  

    def open_maps(self):
        if not self.points or not self.order_nn:
            return
        origin = f"{self.start_loc[0]},{self.start_loc[1]}"
        waypoints = [f"{self.points[i][0]},{self.points[i][1]}" for i in self.order_nn]

        url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}"
            f"&destination={origin}"
            f"&waypoints={'|'.join(waypoints)}"
        )
        webbrowser.open(url)

    def save_locations(self):
        if not self.start_loc or not self.points:
            messagebox.showerror("Error", "No locations to save")
            return
        data = {
            "start": {"lat": self.start_loc[0], "lon": self.start_loc[1]},
            "points": [{"lat": p[0], "lon": p[1], "name": p[2]} for p in self.points]
        }
        fname = "locations.json"
        with open(fname, "w") as f:
            json.dump(data, f)
        messagebox.showinfo("Saved", f"Locations saved to {fname}")

    def load_locations(self):
        fname = "locations.json"
        if not os.path.exists(fname):
            messagebox.showerror("Error", f"{fname} not found")
            return
        with open(fname) as f:
            data = json.load(f)
        self.start_loc = (data["start"]["lat"], data["start"]["lon"])
        self.points = [(p["lat"], p["lon"], p["name"]) for p in data["points"]]
        self.start_entry.delete(0, "end")
        self.start_entry.insert("0", self.points[0][2])
        self.dest_text.delete("1.0", "end")
        for p in self.points:
            self.dest_text.insert("end", f"{p[2]}\n")
        messagebox.showinfo("Loaded", f"Locations loaded from {fname}")

    def show_map_preview(self):
        mp = MapPreview(PIL_AVAILABLE)
        img = mp.generate(self.start_loc, self.points)
        if img:
            img.thumbnail((600, 300))
            self.map_img = ImageTk.PhotoImage(img)
            top = tk.Toplevel(self)
            top.title("Map Preview")
            lbl = tk.Label(top, image=self.map_img)
            lbl.pack()
        else:
            messagebox.showwarning("Map Preview", "PIL not available or failed to fetch map.")


if __name__ == "__main__":
    App().mainloop()
