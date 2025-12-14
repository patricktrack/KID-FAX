"""Helpers for working with ESC/POS printers."""
from __future__ import annotations

import logging
import os
from typing import Optional

from escpos.printer import Network, Serial, Usb

__all__ = ["DummyPrinter", "get_printer", "print_ticket"]

LOGGER = logging.getLogger(__name__)


class DummyPrinter:
    """Minimal stand-in printer that writes output to stdout."""

    def __init__(self) -> None:
        self._header_printed = False

    def set(self, **_: object) -> None:  # pragma: no cover - interface shim
        return

    def text(self, value: str) -> None:
        if not self._header_printed:
            print("[kidfax] --- dummy printer output ---")
            self._header_printed = True
        print(value, end="")

    def ln(self) -> None:
        self.text("\n")

    def cut(self) -> None:
        self.text("\n" + "-" * 32 + "\n")


def _coerce_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            return int(value, 0)
        return int(value)
    except (TypeError, ValueError):
        return default


def _printer_backend() -> str:
    driver = os.getenv("PRINTER_DRIVER") or os.getenv("PRINTER_TYPE", "usb")
    return driver.strip().lower()


def get_printer(*, allow_dummy: bool = False) -> Optional[object]:
    """Return an ESC/POS printer instance based on env configuration."""

    driver = _printer_backend()

    if driver == "dummy":
        LOGGER.warning("Using dummy printer backend.")
        return DummyPrinter()

    try:
        if driver == "usb":
            vendor = _coerce_int(os.getenv("USB_VENDOR"), 0x0416)
            product = _coerce_int(os.getenv("USB_PRODUCT"), 0x5011)
            interface = _coerce_int(os.getenv("USB_INTERFACE"))
            in_ep = _coerce_int(os.getenv("USB_IN_EP"))
            out_ep = _coerce_int(os.getenv("USB_OUT_EP"))
            kwargs = {}
            if interface is not None:
                kwargs["usb_interface"] = interface
            if in_ep is not None:
                kwargs["in_ep"] = in_ep
            if out_ep is not None:
                kwargs["out_ep"] = out_ep
            LOGGER.info(
                "Connecting to USB printer (vendor=%s, product=%s)",
                hex(vendor) if vendor is not None else "?",
                hex(product) if product is not None else "?",
            )
            return Usb(vendor, product, **kwargs)

        if driver in {"serial", "bluetooth"}:
            port = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
            if driver == "bluetooth":
                port = os.getenv("BLUETOOTH_SERIAL_PORT", "/dev/rfcomm0")
            baud = _coerce_int(
                os.getenv("SERIAL_BAUD") or os.getenv("SERIAL_BAUDRATE"),
                9600,
            )
            timeout = float(os.getenv("SERIAL_TIMEOUT", "1"))
            LOGGER.info("Connecting to serial printer on %s @ %sbps", port, baud)
            return Serial(devfile=port, baudrate=baud, timeout=timeout)

        if driver == "network":
            host = os.getenv("NETWORK_HOST", "192.168.1.100")
            port = _coerce_int(os.getenv("NETWORK_PORT"), 9100)
            LOGGER.info("Connecting to network printer %s:%s", host, port)
            return Network(host, port)

        raise ValueError(f"Unknown printer driver '{driver}'")

    except Exception as exc:  # pragma: no cover - hardware interaction
        LOGGER.error("Failed to initialize printer (%s)", exc)
        if allow_dummy:
            LOGGER.warning("Falling back to dummy printer backend for testing.")
            return DummyPrinter()
        return None


def print_ticket(printer: object, from_name: str, question: str) -> bool:
    """Print the original ticket template used by the web UI."""

    from datetime import datetime

    try:
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%B %d, %Y")

        printer.set(align="center", font="a", width=2, height=2, bold=True)
        printer.text("================================\n")
        printer.text("TICKET\n")

        printer.set(align="center", font="a", width=1, height=1, bold=False)
        printer.text("--------------------------------\n")

        printer.set(align="left", font="a", width=1, height=1, bold=True)
        printer.text(f"From: {from_name}\n")

        printer.set(align="left", font="a", width=1, height=1, bold=False)
        printer.text(f"Time: {time_str}\n")
        printer.text(f"Date: {date_str}\n")

        printer.text("--------------------------------\n")

        printer.set(align="left", font="a", width=1, height=1, bold=True)
        printer.text("Question/Comment\n")

        printer.set(align="left", font="a", width=1, height=1, bold=False)
        printer.text(f"{question}\n")

        printer.text("--------------------------------\n")

        printer.set(align="center", font="a", width=2, height=2, bold=True)
        printer.text("================================\n")

        printer.text("\n\n")
        printer.cut()
        return True
    except Exception as exc:  # pragma: no cover - hardware interaction
        LOGGER.error("Error printing ticket: %s", exc)
        return False
