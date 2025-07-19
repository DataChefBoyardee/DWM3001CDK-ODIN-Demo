#!/bin/bash

DEVICE_FILE=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | while read -r dev; do if udevadm info -a -n $dev | grep -q 'ATTRS{idVendor}=="1915"' && udevadm info -a -n $dev | grep -q 'ATTRS{idProduct}=="520f"'; then echo "$dev"; break; fi; done); \
	if [ -z "$DEVICE_FILE" ]; then echo "Device not found"; exit 1; 
        else echo $DEVICE_FILE 
        fi; \
	
