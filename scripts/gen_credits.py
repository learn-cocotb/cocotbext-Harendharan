import cocotb
from cocotb.regression import TestFactory
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase
from cocotb.result import TestFailure

class Scoreboard:
    """A simple scoreboard to track the DFF outputs."""
    def __init__(self):
        self.expected = None
        self.actual = None

    def add_expected(self, expected_value):
        """Add expected output."""
        self.expected = expected_value

    def add_actual(self, actual_value):
        """Add actual output."""
        self.actual = actual_value

    def check(self):
        """Check if actual matches expected."""
        if self.expected != self.actual:
            raise TestFailure(f"Scoreboard mismatch: expected {self.expected}, but got {self.actual}")
        else:
            print(f"Scoreboard check passed: expected {self.expected} and got {self.actual}")

# Testbench function
@cocotb.coroutine
async def run_dff_tb(dut):
    """Run the D Flip-Flop testbench."""
    # Create a clock signal with a period of 10ns
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset the DUT
    dut.rst <= 1
    dut.d <= 0
    await cocotb.start(dut._wait_for_simulation())

    # Initialize scoreboard
    scoreboard = Scoreboard()

    # Apply reset and check if output is 0
    await rising_edge(dut.clk)
    dut.rst <= 0  # Remove reset
    scoreboard.add_expected(0)  # Initial value of Q should be 0 (reset condition)
    scoreboard.add_actual(dut.q.value)
    scoreboard.check()

    # Apply a test case: set D = 1, expect Q to be 1
    dut.d <= 1
    await rising_edge(dut.clk)
    scoreboard.add_expected(1)  # Q should follow D after a clock cycle
    scoreboard.add_actual(dut.q.value)
    scoreboard.check()

    # Apply a test case: set D = 0, expect Q to be 0
    dut.d <= 0
    await rising_edge(dut.clk)
    scoreboard.add_expected(0)  # Q should follow D after a clock cycle
    scoreboard.add_actual(dut.q.value)
    scoreboard.check()

    
