 def log(self, s: str, level: int = 1):
        """
        level:
          0 = errores críticos
          1 = normal (default)
          2 = verbose / debug
        """

        if self.verbose < level:
            return

        # Timestamp (año 2 cifras)
        now = datetime.now().strftime("[%d/%m/%y-%H:%M:%S]")

        # Sanitiza para que no te machaque el timestamp
        s = str(s).replace("\r", "").rstrip("\n")

        with self.print_lock:
            if s.startswith("[RX"):
                color = ANSI_GREEN
            elif s.startswith("[TX") or s.startswith("[ACK"):
                color = ANSI_YELLOW
            elif s.startswith("[RETRY") or s.startswith("[FAIL"):
                color = ANSI_RED
            elif s.startswith("[ERR"):
                color = ANSI_MAGENTA
            elif s.startswith("[DEBUG"):
                color = ANSI_CYAN
            else:
                color = ANSI_CYAN

            #print(f"{ANSI_RESET}{now} {color}{s}{ANSI_RESET}", flush=True)
            line_plain = f"{now} {s}"
            line_console = f"{ANSI_RESET}{now} {color}{s}{ANSI_RESET}"

            # consola
            if self.log_mode in ("console", "both"):
                print(line_console, flush=True)

            # archivo (sin ANSI, siempre limpio)
            if self.log_mode in ("file", "both") and self._log_fh:
                self._log_fh.write(strip_ansi(line_plain) + "\n")
