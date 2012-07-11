from blinker import Namespace

proccer_signals = Namespace()
report_received = proccer_signals.signal('report-received')
