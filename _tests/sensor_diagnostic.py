#!/usr/bin/env python3
"""
I2C Sensor Diagnostic Tool for Bedrock App
Tests ENS160 and AHT21 sensors with correct addresses
"""
import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SensorDiagnostic")

# Define constants for I2C addresses
ENS160_ADDRESS = 0x53  # Correct address for ENS160
AHT21_ADDRESS = 0x38   # Address for AHT21

print("=" * 60)
print("   I2C SENSOR DIAGNOSTIC FOR ENS160 AND AHT21 SENSORS")
print("=" * 60)
print(f"ENS160 Address: 0x{ENS160_ADDRESS:02X}")
print(f"AHT21 Address:  0x{AHT21_ADDRESS:02X}")
print("-" * 60)

# Check for I2C devices
print("\n1. Checking I2C devices:")
if os.path.exists("/dev/i2c-1"):
    print("✓ Device /dev/i2c-1 found")
    i2c_dev = "/dev/i2c-1"
elif os.path.exists("/dev/i2c-0"):
    print("✓ Device /dev/i2c-0 found")
    i2c_dev = "/dev/i2c-0"
else:
    print("✗ No I2C devices found. Is I2C enabled?")
    print("  Run: sudo raspi-config")
    print("  Select: Interfacing Options > I2C > Enable")
    sys.exit(1)

# Check permissions
try:
    with open(i2c_dev, "rb"):
        print("✓ I2C permissions OK")
except PermissionError:
    print("✗ Permission error accessing I2C device")
    print(f"  Run: sudo chmod 666 {i2c_dev}")
    sys.exit(1)

# Check required libraries
print("\n2. Checking required libraries:")
libs_ok = True

try:
    import board
    import busio
    print("✓ board and busio modules available")
except ImportError:
    print("✗ board and busio modules missing")
    print("  Run: pip3 install adafruit-blinka")
    libs_ok = False

try:
    import adafruit_ens160
    print("✓ adafruit_ens160 module available")
except ImportError:
    print("✗ adafruit_ens160 module missing")
    print("  Run: pip3 install adafruit-circuitpython-ens160")
    libs_ok = False

try:
    import adafruit_ahtx0
    print("✓ adafruit_ahtx0 module available")
except ImportError:
    print("✗ adafruit_ahtx0 module missing")
    print("  Run: pip3 install adafruit-circuitpython-ahtx0")
    libs_ok = False

if not libs_ok:
    print("\nPlease install missing libraries and try again")
    sys.exit(1)

# Initialize I2C
print("\n3. Initializing I2C:")
i2c = None

try:
    print("   Trying Method 1 (board.SCL, board.SDA)...")
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✓ I2C initialized with board.SCL/board.SDA")
except Exception as e:
    print(f"✗ Method 1 failed: {e}")
    
    try:
        print("   Trying Method 2 (GPIO 3, 2)...")
        i2c = busio.I2C(3, 2)  # GPIO3=SCL, GPIO2=SDA for Pi 5
        print("✓ I2C initialized with GPIO pins 3 and 2")
    except Exception as e:
        print(f"✗ Method 2 failed: {e}")
        
        try:
            print("   Trying Method 3 (direct I2C device)...")
            from adafruit_blinka.microcontroller.generic_linux.i2c import I2C
            i2c = I2C(1 if i2c_dev == "/dev/i2c-1" else 0)
            print("✓ I2C initialized with direct I2C device")
        except Exception as e:
            print(f"✗ Method 3 failed: {e}")
            print("\nFailed to initialize I2C. Check your wiring and libraries.")
            sys.exit(1)

# Scan I2C bus
print("\n4. Scanning I2C bus:")
devices = []
try:
    for address in range(0x00, 0x80):
        try:
            i2c.writeto(address, b'')
            devices.append(address)
        except:
            pass
            
    if devices:
        print(f"✓ Found {len(devices)} I2C devices:")
        for address in devices:
            device_type = ""
            if address == ENS160_ADDRESS:
                device_type = "ENS160 sensor"
            elif address == AHT21_ADDRESS:
                device_type = "AHT21 sensor"
                
            print(f"   0x{address:02X} {device_type}")
        
        # Check for our specific sensors
        if ENS160_ADDRESS not in devices:
            print(f"✗ ENS160 not found at address 0x{ENS160_ADDRESS:02X}")
        if AHT21_ADDRESS not in devices:
            print(f"✗ AHT21 not found at address 0x{AHT21_ADDRESS:02X}")
    else:
        print("✗ No I2C devices found on the bus!")
        print("  Check your wiring connections")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error scanning I2C: {e}")
    sys.exit(1)

# Test sensor readings
print("\n5. Testing sensor readings:")

# Test ENS160
if ENS160_ADDRESS in devices:
    try:
        print("   Testing ENS160 sensor...")
        ens = adafruit_ens160.ENS160(i2c, address=ENS160_ADDRESS)
        
        # Get multiple readings
        print("   Taking 3 readings with 1 second intervals...")
        for i in range(3):
            if i > 0:
                time.sleep(1)
            
            eco2 = ens.eCO2
            tvoc = ens.TVOC
            aqi = ens.AQI
            
            print(f"   Reading {i+1}: eCO2={eco2} ppm, TVOC={tvoc} ppb, AQI={aqi}")
        
        print("✓ ENS160 sensor working!")
    except Exception as e:
        print(f"✗ Error reading ENS160: {e}")
else:
    print("✗ Skipping ENS160 test (device not found)")

# Test AHT21
if AHT21_ADDRESS in devices:
    try:
        print("   Testing AHT21 sensor...")
        aht = adafruit_ahtx0.AHTx0(i2c, address=AHT21_ADDRESS)
        
        # Get multiple readings
        print("   Taking 3 readings with 1 second intervals...")
        for i in range(3):
            if i > 0:
                time.sleep(1)
            
            temp = aht.temperature
            humid = aht.relative_humidity
            
            print(f"   Reading {i+1}: Temperature={temp:.1f}°C, Humidity={humid:.1f}%")
        
        print("✓ AHT21 sensor working!")
    except Exception as e:
        print(f"✗ Error reading AHT21: {e}")
else:
    print("✗ Skipping AHT21 test (device not found)")

# Check environment variables
print("\n6. Checking environment variables:")
use_mock = os.environ.get("USE_MOCK_SENSORS")
if use_mock == "1":
    print("✗ USE_MOCK_SENSORS=1 (using mock sensors)")
    print("  To use real sensors, set USE_MOCK_SENSORS=0 in start.sh")
else:
    print(f"✓ USE_MOCK_SENSORS={use_mock or 'not set'} (real sensors enabled)")

print("\n=== DIAGNOSTIC COMPLETE ===")