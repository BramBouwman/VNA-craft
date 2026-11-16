import csv
import argparse
import math
import re
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from qratio_plugin import QratioPlugin


def format_display(value, unit=""):
    text = "%.2f" % value
    return "%s %s" % (text, unit) if unit else text


class VnaWorker:
    def __init__(self, events):
        self.events = events
        self.commands = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.running = True
        self.connected = False
        self.trigger_source = "BUS"
        self.thread.start()

    def call(self, command, *args):
        self.commands.put((command, args))

    def close(self):
        self.running = False
        self.commands.put(("close", ()))

    def _run(self):
        app = None
        pythoncom = None
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            while self.running:
                try:
                    command, args = self.commands.get(timeout=0.1)
                except queue.Empty:
                    continue
                if command == "connect":
                    try:
                        app = win32com.client.Dispatch("TRVNA.Application")
                        trigger_source = args[0]
                        if trigger_source not in ("BUS", "INT"):
                            raise ValueError("Ongeldige triggerbron: %s" % trigger_source)
                        app.SCPI.TRIGger.SEQuence.SOURce = trigger_source
                        self.trigger_source = trigger_source
                        self.connected = True
                        self.events.put(("status", "Verbonden; triggerbron %s" % trigger_source))
                    except Exception as exc:
                        app = None
                        self.events.put(("error", "Verbinden mislukt: %s" % exc))
                elif command == "read":
                    if app is None:
                        self.events.put(("error", "Geen verbinding met de VNA."))
                        continue
                    try:
                        values = self._trigger_and_read_source(
                            app, args[0], args[1], self.trigger_source
                        )
                        self.events.put(("data", values))
                    except Exception as exc:
                        self.events.put(("read_error", str(exc)))
                elif command == "close":
                    break
        except ImportError:
            self.events.put(("error", "pywin32 ontbreekt. Voer install.bat uit."))
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()

    @staticmethod
    def _trigger_and_read_source(app, channel, marker, trigger_source):
        if trigger_source == "BUS":
            try:
                sequence = app.SCPI.TRIGger.SEQuence
                sequence.SOURce = "BUS"
                sequence.SINGle()
            except Exception as exc:
                raise RuntimeError("BUS single trigger mislukt: %s" % exc) from exc
        return VnaWorker._read_bandwidth_data(app, channel, marker)

    @staticmethod
    def _read_bandwidth_data(app, channel, marker):
        # TRVNA exposes DATA as a COM property in some builds and as a
        # zero-argument method in others.
        try:
            calc = app.SCPI.GetCALCulate(channel)
        except Exception as exc:
            raise RuntimeError(            "SCPI.GetCALCulate(%s): %s" % (channel, exc)) from exc
        try:
            marker_obj = calc.SELected.GetMARKer(marker)
        except Exception as exc:
            raise RuntimeError(
            "SCPI.GetCALCulate(%s).SELected.GetMARKer(%s): %s"
                % (channel, marker, exc)
            ) from exc
        try:
            data_member = marker_obj.BWIDth.DATA
        except Exception as exc:
            raise RuntimeError(
                "BWIDth.DATA ontbreekt. Activeer Bandwidth Search/Marker Math "
                "voor deze marker. COM-fout: %s" % exc
            ) from exc
        data = data_member() if callable(data_member) else data_member
        values = [float(data[index]) for index in range(4)]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("VNA gaf een niet-finite waarde terug")
        bandwidth, center, q_value, loss = values
        return {
            "bandwidth_hz": bandwidth,
            "center_hz": center,
            "q": q_value,
            "loss": loss,
        }


class QmaxMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VNA-Craft Beta 3 - Copper Mountain TR1300/1")
        self.geometry("1000x720")
        self.minsize(720, 520)
        self._configure_dark_theme()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.events = queue.Queue()
        self.worker = VnaWorker(self.events)
        self.samples = []
        self.measuring = False
        self.started_at = None
        self.error_count = 0
        self.measurement_saved = False
        self.read_after_id = None
        self.qratio = QratioPlugin()
        self.after(100, self._process_events)
        self._build_ui()

    def _configure_dark_theme(self):
        background = "#171A20"
        panel = "#20252D"
        elevated = "#282E38"
        foreground = "#E8EDF4"
        muted = "#929DAC"
        button_active = "#344255"
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=panel, foreground=foreground, font=("Segoe UI", 9))
        style.configure("TLabel", background=panel, foreground=foreground)
        style.configure("TLabelframe", background=panel, foreground=muted)
        style.configure("TLabelframe.Label", background=panel, foreground=muted)
        style.configure("TFrame", background=panel)
        style.configure(
            "TButton", background=elevated, foreground=foreground,
            bordercolor="#3A4452", lightcolor="#3A4452", darkcolor="#11151B",
            focuscolor="#3A4452", padding=(10, 5),
        )
        style.map(
            "TButton",
            background=[("active", button_active), ("pressed", "#101010")],
            foreground=[("active", foreground), ("pressed", foreground)],
        )
        style.configure("TEntry", fieldbackground="#101317", foreground=foreground, insertcolor=foreground)
        style.configure(
            "TSpinbox", fieldbackground="#101317", foreground=foreground,
            arrowcolor=foreground,
        )
        style.configure("TCombobox", fieldbackground="#101317", foreground=foreground)
        self.configure(background=background)
        self.dark_background = background
        self.dark_foreground = foreground

    def _build_ui(self):
        settings = ttk.LabelFrame(self, text="Instellingen", padding=6)
        settings.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(settings, text="Channel").grid(row=0, column=0, padx=5, pady=5)
        self.channel = tk.IntVar(value=1)
        ttk.Spinbox(settings, from_=1, to=16, width=6, textvariable=self.channel).grid(row=0, column=1)
        ttk.Label(settings, text="Marker").grid(row=0, column=2, padx=5)
        self.marker = tk.IntVar(value=1)
        ttk.Spinbox(settings, from_=1, to=16, width=6, textvariable=self.marker).grid(row=0, column=3)
        ttk.Label(settings, text="Interval (s)").grid(row=0, column=4, padx=5)
        self.interval = tk.StringVar(value="0.01")
        ttk.Entry(settings, width=8, textvariable=self.interval).grid(row=0, column=5)
        ttk.Label(settings, text="Coilnaam").grid(row=0, column=6, padx=5)
        self.coil_name = tk.StringVar()
        ttk.Entry(settings, width=18, textvariable=self.coil_name).grid(row=0, column=7)
        ttk.Label(settings, text="Trigger").grid(row=0, column=8, padx=5)
        self.trigger_source = tk.StringVar(value="BUS")
        ttk.Combobox(
            settings, width=6, state="readonly",
            textvariable=self.trigger_source, values=("BUS", "INT"),
        ).grid(row=0, column=9)
        settings_buttons = ttk.Frame(settings)
        settings_buttons.grid(row=1, column=0, columnspan=10, sticky="w", padx=5, pady=(4, 2))
        ttk.Button(
            settings_buttons, text="Verbinden",
            command=lambda: self.worker.call("connect", self.trigger_source.get()),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            settings_buttons, text="Start registratie", command=self.start,
        ).pack(side="left", padx=4)
        ttk.Button(settings_buttons, text="Stop", command=self.stop).pack(side="left", padx=4)
        ttk.Button(settings_buttons, text="Reset", command=self.reset).pack(side="left", padx=4)
        ttk.Button(settings_buttons, text="Start Qratio", command=self.start_qratio).pack(side="left", padx=(12, 4))

        values = ttk.LabelFrame(self, text="Meetwaarden", padding=6)
        values.pack(fill="x", padx=10, pady=(0, 6))
        self.labels = {}
        for index, (key, title, unit) in enumerate((
                ("q", "Huidige Q", ""), ("qmax", "Qmax", ""),
                ("q_top3_avg", "Gemiddelde top 3 Q", ""),
                ("qmax_center_hz", "Frequentie bij Qmax", "MHz"),
                ("center_hz", "Middenfrequentie", "MHz"),
                ("bandwidth_hz", "Bandwidth", "MHz"),
                ("elapsed", "Meetduur", "s"), ("count", "Meetpunten", ""))):
            label_column = (index % 2) * 2
            value_column = label_column + 1
            values.columnconfigure(label_column, minsize=140, weight=1)
            values.columnconfigure(value_column, minsize=120, weight=1)
            ttk.Label(values, text=title + ":").grid(
                row=index // 2, column=label_column, sticky="e", padx=5, pady=4
            )
            label = ttk.Label(values, text="- " + unit, width=18)
            label.grid(row=index // 2, column=value_column, sticky="w", padx=5)
            self.labels[key] = label

        self.canvas = tk.Canvas(
            self, height=350, background="#101317",
            highlightbackground="#3A4452", highlightcolor="#3A4452",
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        actions = ttk.Frame(self, padding=(10, 4, 10, 10))
        actions.pack(fill="x")
        ttk.Button(actions, text="Exporteer CSV", command=self.export_csv).pack(side="left")
        ttk.Button(actions, text="Exporteer Excel", command=self.export_excel).pack(side="left", padx=5)
        self.status = ttk.Label(actions, text="Niet verbonden")
        self.status.pack(side="right")
        self.qratio_status = ttk.Label(actions, text="Qratio uit", foreground="#929DAC")
        self.qratio_status.pack(side="right", padx=12)

    def start(self):
        if self.measuring:
            return
        if not self.coil_name.get().strip():
            messagebox.showerror("Coilnaam ontbreekt", "Geef eerst een coilnaam op.")
            return
        try:
            interval = float(self.interval.get().replace(",", "."))
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ongeldig interval", "Geef een positief interval in seconden op.")
            return
        self.samples = []
        self.error_count = 0
        self.measurement_saved = False
        self.measuring = True
        self.started_at = time.monotonic()
        self._schedule_read(0)
        self.status.configure(text="Registratie actief")

    def start_qratio(self):
        if self.measuring:
            return
        if not self.coil_name.get().strip():
            messagebox.showerror("Coilnaam ontbreekt", "Geef eerst een coilnaam op.")
            return
        self.qratio.begin()
        self.qratio_status.configure(text="Qratio: UNLOADED - druk Start registratie")
        self.status.configure(text="Plaats unloaded coil en start de registratie")

    def restart_qratio(self):
        self.stop()
        self.qratio.begin()
        self.samples = []
        self.qratio_status.configure(text="Qratio: UNLOADED - opnieuw gestart")
        self.status.configure(text="Plaats unloaded coil en start de registratie")

    def _schedule_read(self, delay_ms):
        if self.measuring:
            self.read_after_id = self.after(delay_ms, self._request_read)

    def _request_read(self):
        if not self.measuring:
            return
        self.worker.call("read", self.channel.get(), self.marker.get())
        try:
            delay = max(1, int(float(self.interval.get().replace(",", ".")) * 1000))
        except ValueError:
            delay = 500
        self._schedule_read(delay)

    def stop(self):
        if self.read_after_id is not None:
            self.after_cancel(self.read_after_id)
            self.read_after_id = None
        qratio_phase = self.qratio.active and self.qratio.phase in ("unloaded", "loaded")
        next_qratio_phase = None
        if qratio_phase:
            try:
                next_qratio_phase = self.qratio.stop_phase(self.samples)
            except (RuntimeError, ValueError) as exc:
                messagebox.showerror("Qratio", str(exc))
                self.qratio.active = False
        if self.measuring and self.samples and not self.measurement_saved:
            try:
                paths = self._save_measurement()
                self.measurement_saved = True
                self.status.configure(text="Opgeslagen: %s" % paths[0].name)
            except (OSError, ImportError) as exc:
                self.error_count += 1
                self.status.configure(text="Opslaan mislukt")
                if self.error_count <= 2:
                    messagebox.showerror("Automatisch opslaan", str(exc))
        self.measuring = False
        if qratio_phase and next_qratio_phase == "loaded":
            self.samples = []
            self.measurement_saved = False
            self.qratio_status.configure(text="Qratio: LOADED - druk Start registratie")
            self.status.configure(text="Unloaded opgeslagen; plaats loaded coil")
        elif qratio_phase and next_qratio_phase == "complete":
            result = self.qratio.result()
            self.qratio_status.configure(text="Qratio: %.2f" % result["qratio"])
            self.status.configure(
                text="Qratio klaar: unloaded %.2f / loaded %.2f"
                % (result["unloaded_average"], result["loaded_average"])
            )
            self.qratio.active = False
        if not self.measurement_saved and not qratio_phase:
            self.status.configure(text="Registratie gestopt")

    def reset(self):
        self.stop()
        self.samples = []
        self.started_at = None
        for key in self.labels:
            self.labels[key].configure(text="-")
        self.canvas.delete("all")
        self.start()

    def _process_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "data" and self.measuring:
                    value["timestamp"] = datetime.now().isoformat(timespec="milliseconds")
                    value["elapsed_s"] = time.monotonic() - self.started_at
                    self.samples.append(value)
                    self._update_values(value)
                    self._draw_graph()
                elif kind == "status":
                    self.status.configure(text=value)
                elif kind == "read_error":
                    self.measuring = False
                    self.status.configure(text="Uitlezen gestopt door fout")
                    self.error_count += 1
                    if self.error_count <= 2:
                        messagebox.showerror(
                            "VNA-uitlezing",
                            "Q-uitlezing mislukt:\n%s\n\n"
                            "Controleer of Bandwidth Search/Marker Math actief is "
                            "voor de gekozen marker en of Channel/Marker kloppen."
                            % value,
                        )
                elif kind == "error":
                    self.status.configure(text="Fout")
                    self.error_count += 1
                    if self.error_count <= 2:
                        messagebox.showerror("VNA", value)
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _update_values(self, value):
        qmax_sample = max(self.samples, key=lambda sample: sample["q"])
        top_three = sorted(
            (sample["q"] for sample in self.samples if sample["q"] > 0),
            reverse=True,
        )[:3]
        top_three_average = sum(top_three) / len(top_three) if top_three else 0
        for key, text in {
            "q": format_display(value["q"]),
            "qmax": format_display(qmax_sample["q"]),
            "q_top3_avg": format_display(top_three_average),
            "qmax_center_hz": format_display(qmax_sample["center_hz"] / 1e6, "MHz"),
            "center_hz": format_display(value["center_hz"] / 1e6, "MHz"),
            "bandwidth_hz": format_display(value["bandwidth_hz"] / 1e6, "MHz"),
            "elapsed": "%.1f s" % value["elapsed_s"],
            "count": str(len(self.samples)),
        }.items():
            self.labels[key].configure(text=text)

    def _draw_graph(self):
        self.canvas.delete("all")
        if len(self.samples) < 1:
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        plotted_samples = [sample for sample in self.samples if sample["q"] != 0]
        if not plotted_samples:
            return
        q_values = [sample["q"] for sample in plotted_samples]
        q_min, q_max = min(q_values), max(q_values)
        q_range = q_max - q_min or 1
        elapsed_max = plotted_samples[-1]["elapsed_s"] or 1
        points = []
        for sample in plotted_samples:
            x = 35 + (width - 50) * sample["elapsed_s"] / elapsed_max
            y = height - 25 - (height - 45) * (sample["q"] - q_min) / q_range
            points.extend((x, y))
        self.canvas.create_text(5, 5, anchor="nw", text="Q", fill=self.dark_foreground)
        self.canvas.create_line(30, 10, 30, height - 20, fill="#9aa0a6")
        self.canvas.create_line(30, height - 20, width - 10, height - 20, fill="#9aa0a6")
        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#8ab4f8", width=2)
        self.canvas.create_text(
            35, 10, anchor="nw",
            text="max %s" % format_display(q_max),
            fill=self.dark_foreground,
        )

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV", "*.csv"),))
        if not path:
            return
        self._save_csv(Path(path))

    def _save_csv(self, path):
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=("timestamp", "q", "bandwidth_mhz", "center_mhz", "loss", "elapsed_s", "is_qmax"),
            )
            writer.writeheader()
            qmax_sample = max(self.samples, key=lambda sample: sample["q"], default=None)
            for sample in self.samples:
                writer.writerow({
                    "timestamp": sample["timestamp"], "q": sample["q"],
                    "bandwidth_mhz": sample["bandwidth_hz"] / 1e6,
                    "center_mhz": sample["center_hz"] / 1e6,
                    "loss": sample["loss"], "elapsed_s": sample["elapsed_s"],
                    "is_qmax": sample is qmax_sample,
                })

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=(("Excel", "*.xlsx"),))
        if not path:
            return
        try:
            self._save_excel(Path(path))
        except ImportError:
            messagebox.showerror("Excel-export", "openpyxl ontbreekt. Voer install.bat uit.")

    def _save_excel(self, path):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        headers = ("timestamp", "q", "bandwidth_mhz", "center_mhz", "loss", "elapsed_s", "is_qmax")
        sheet.append(headers)
        qmax_sample = max(self.samples, key=lambda sample: sample["q"], default=None)
        for sample in self.samples:
            sheet.append([
                sample["timestamp"], sample["q"], sample["bandwidth_hz"] / 1e6,
                sample["center_hz"] / 1e6, sample["loss"], sample["elapsed_s"],
                sample is qmax_sample,
            ])
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 18
        workbook.save(path)

    def _save_measurement(self):
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", self.coil_name.get().strip()).strip("._")
        if not safe_name:
            raise OSError("De coilnaam bevat geen geldige bestandsnaamtekens.")
        folder = Path(__file__).resolve().parent / "metingen"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = folder / ("%s_%s" % (safe_name, stamp))
        csv_path = base.with_suffix(".csv")
        xlsx_path = base.with_suffix(".xlsx")
        self._save_csv(csv_path)
        self._save_excel(xlsx_path)
        return csv_path, xlsx_path

    def _close(self):
        self.measuring = False
        self.worker.close()
        self.destroy()


def run_headless(channel, marker, interval, output, trigger_source):
    events = queue.Queue()
    worker = VnaWorker(events)
    worker.call("connect", trigger_source)
    connected = False
    samples = []
    started_at = time.monotonic()
    try:
        while not connected:
            kind, value = events.get(timeout=10)
            if kind == "status":
                connected = True
                print(value, flush=True)
            elif kind in ("error", "read_error"):
                raise RuntimeError(value)
        print("Headless registratie actief; druk Ctrl+C om te stoppen.", flush=True)
        while True:
            worker.call("read", channel, marker)
            kind, value = events.get(timeout=max(10, interval + 10))
            if kind == "data":
                value["timestamp"] = datetime.now().isoformat(timespec="milliseconds")
                value["elapsed_s"] = time.monotonic() - started_at
                samples.append(value)
                print(
                    "%s: Q=%s, center=%s MHz, bandwidth=%s MHz"
                    % (
                        value["timestamp"], format_display(value["q"]),
                        format_display(value["center_hz"] / 1e6),
                        format_display(value["bandwidth_hz"] / 1e6),
                    ),
                    flush=True,
                )
            elif kind in ("error", "read_error"):
                raise RuntimeError(value)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()
        if samples:
            with open(output, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=("timestamp", "q", "bandwidth_mhz", "center_mhz", "loss", "elapsed_s"),
                )
                writer.writeheader()
                for sample in samples:
                    writer.writerow({
                        "timestamp": sample["timestamp"], "q": sample["q"],
                        "bandwidth_mhz": sample["bandwidth_hz"] / 1e6,
                        "center_mhz": sample["center_hz"] / 1e6,
                        "loss": sample["loss"], "elapsed_s": sample["elapsed_s"],
                    })
            print("Opgeslagen: %s (%d meetpunten)" % (output, len(samples)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VNA-craft voor TRVNA")
    parser.add_argument("--headless", action="store_true", help="Draai zonder GUI; stop met Ctrl+C")
    parser.add_argument("--channel", type=int, default=1)
    parser.add_argument("--marker", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.01)
    parser.add_argument("--output", default="qmax_headless.csv")
    parser.add_argument("--trigger", choices=("BUS", "INT"), default="BUS")
    arguments = parser.parse_args()
    if arguments.interval <= 0:
        parser.error("--interval moet positief zijn")
    if arguments.headless:
        run_headless(
            arguments.channel, arguments.marker, arguments.interval,
            arguments.output, arguments.trigger,
        )
    else:
        QmaxMonitor().mainloop()
