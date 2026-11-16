class QratioPlugin:
    """Guided two-phase Qratio calculation for a measurement window."""

    def __init__(self):
        self.active = False
        self.phase = None
        self.unloaded = []
        self.loaded = []

    def begin(self):
        self.active = True
        self.phase = "unloaded"
        self.unloaded = []
        self.loaded = []

    def start_phase(self):
        if not self.active or self.phase is None:
            raise RuntimeError("Start eerst de Qratio-workflow.")

    def stop_phase(self, samples):
        self.start_phase()
        values = [sample["q"] for sample in samples if sample["q"] > 0]
        if self.phase == "unloaded":
            self.unloaded = values
            self.phase = "loaded"
            return "loaded"
        self.loaded = values
        self.phase = "complete"
        return "complete"

    def restart_phase(self):
        self.start_phase()
        if self.phase == "unloaded":
            self.unloaded = []
        elif self.phase == "loaded":
            self.loaded = []

    def result(self):
        if not self.unloaded or not self.loaded:
            return None
        unloaded_average = sum(self.unloaded) / len(self.unloaded)
        loaded_average = sum(self.loaded) / len(self.loaded)
        if loaded_average == 0:
            raise ZeroDivisionError("Gemiddelde loaded Q is nul.")
        return {
            "unloaded_average": unloaded_average,
            "loaded_average": loaded_average,
            "qratio": unloaded_average / loaded_average,
        }
