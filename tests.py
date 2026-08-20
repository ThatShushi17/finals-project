from pathlib import Path
import sys
import unittest
import time


class ColoredTextTestResult(unittest.TextTestResult):
    """Custom test result class with colored and formatted output."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_times = {}
        self.current_test_start = None
        self.current_class = None
    
    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def startTest(self, test):
        super().startTest(test)
        self.current_test_start = time.time()
        test_class = test.__class__.__name__
        if test_class != self.current_class:
            self.current_class = test_class
            if self.testsRun > 0:
                self.stream.write("\n")
            self.stream.write(f"\n{self.BLUE}{self.BOLD}→ {test_class}{self.RESET}\n")
    
    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.time() - self.current_test_start
        test_name = test._testMethodName
        self.stream.write(f"  {self.GREEN}PASS{self.RESET} {test_name} ({elapsed:.3f}s)\n\n")
        self.stream.flush()
    
    def addError(self, test, err):
        super().addError(test, err)
        test_name = test._testMethodName
        self.stream.write(f"  {self.RED}ERROR{self.RESET} {test_name}\n\n")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_name = test._testMethodName
        self.stream.write(f"  {self.RED}FAIL{self.RESET} {test_name}\n\n")


class ColoredTextTestRunner(unittest.TextTestRunner):
    """Custom test runner using colored output."""
    resultclass = ColoredTextTestResult


PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"


if __name__ == "__main__":
    if not TESTS_DIR.exists():
        print(f"Tests directory not found: {TESTS_DIR}")
        sys.exit(1)

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test*.py",
        top_level_dir=str(PROJECT_ROOT),
    )
    
    runner = ColoredTextTestRunner(verbosity=2)
    print(f"\n{ColoredTextTestResult.BOLD}Running Tests{ColoredTextTestResult.RESET}")
    print("=" * 50)
    
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print(f"{ColoredTextTestResult.GREEN}{ColoredTextTestResult.BOLD}All tests passed!{ColoredTextTestResult.RESET}")
    else:
        print(f"{ColoredTextTestResult.RED}{ColoredTextTestResult.BOLD}Some tests failed{ColoredTextTestResult.RESET}")
    
    print(f"Tests run: {result.testsRun} | Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("=" * 50 + "\n")
    
    sys.exit(0 if result.wasSuccessful() else 1)
