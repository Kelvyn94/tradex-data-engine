from backend.utils.logger import log


class ReportService:

    def __init__(self):

        self.success = 0

        self.failed = 0

    def ok(self):

        self.success += 1

    def fail(self):

        self.failed += 1

    def summary(self):

        log("")

        log("==============")

        log("DOWNLOAD REPORT")

        log("==============")

        log(f"Successful : {self.success}")

        log(f"Failed     : {self.failed}")