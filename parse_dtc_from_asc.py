import re
import sys
import time

# Print control variables
PRINT_DM1_SINGLE_FRAME = False
PRINT_TP_CT = False
PRINT_TP_DT = False
PRINT_J1939TP_FECAp = False
PRINT_TP_DM1_MULTI_FRAME = False
PRINT_INCORRET_ORDER = False
PRINT_DM1_PARSED = True

# control variable for emulating time
EMULATE_TIME = False
# To keep track of the last timestamp for time emulation  
last_time = 0.0 

# Function to parse BAM TP:CT message
def parse_tp_ct_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    control_byte = data_bytes[0]

    # Check if it's a BAM message 0x20 (32)
    if control_byte == '20': 
        total_size = int(data_bytes[2] + data_bytes[1], 16)
        num_packets = int(data_bytes[3], 16)
        reserved = data_bytes[4]
        pgn = int(data_bytes[7] + data_bytes[6] + data_bytes[5], 16)
        return timestamp, message_id, total_size, num_packets, pgn
    else:
        sys.exit(f'**** NOT BAM MESSAGE, MSG TYPE IS 0x{control_byte}')
    return None

# Function to parse BAM TP.DT message
def parse_tp_dt_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    packet_number = int(data_bytes[0], 16)
    data = data_bytes[1:8]
    return timestamp, message_id, packet_number, data

# Check if the second byte of the CAN identifier is EC
def is_tp_cm_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:4] == 'EC'

# Check if the second byte of the CAN identifier is EB
def is_tp_dt_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:4] == 'EB'

# Check if the second and third bytes of the CAN identifier are FECA
def is_dm1_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:6] == 'FECA'

# Convert each byte to an 8-bit binary string and join all into one string
def bytes_to_binary_string(byte_list):
    binary_string = ''.join(format(byte, '08b') for byte in byte_list)
    return binary_string

# Function to parse DM1 message
def parse_dm1_message(timestamp, src, data_bytes):
    # print(data_bytes)
    # binary_str = bytes_to_binary_string(data_bytes)
    # print(binary_str)
    # spn_start = 2*8
    # spn1 = binary_str[spn_start: spn_start + 8]
    # #print('SPN 1', spn1)
    # spn2 = binary_str[spn_start + 8: spn_start + 16]
    # #print('SPN 2', spn2)
    # spn3 = binary_str[spn_start + 16: spn_start + 16 + 3]
    # # print('SPN 3', spn3)
    # spn = spn3 + spn2 + spn1
    # print('SPN', spn, int(spn,2), hex(int(spn, 2)))
    # start = (4*8)+3
    # aux = binary_str[start : start+5]
    # print('FMI_AUX', aux, int(aux, 2))
    # start = (5*8)+1
    # aux = binary_str[start : start+7]
    # print('OC_AUX', aux, int(aux, 2))

    float_timestamp = float(timestamp)
    if EMULATE_TIME:
        global last_time
        if last_time != 0:
            time_diff = ffloat_timestamp - last_time
            if time_diff > 0:
                time.sleep(time_diff)
        last_time = float_timestamp

    mil = (data_bytes[0] >> 6) & 0x03 # byte1, 2bits, Malfunction Indicator Lamp status
    rsl = (data_bytes[0] >> 4) & 0x03 # byte1, 2bits, Red Stop Lamp status
    awl = (data_bytes[0] >> 2) & 0x03 # byte1, 2bits, Amber Warning Lamp status
    pl = data_bytes[0] & 0x03 # byte1, 2bits, Protect Lamp status
    rfu = data_bytes[1] # byte2, reserved
    if PRINT_DM1_PARSED:
        print(f"DM1 -> Time: {timestamp}, SRC: 0x{src} ({int(src, 16)}), MIL: {mil}, RSL: {rsl}, AWL: {awl}, PL: {pl}")
    
    # starting at third byte, iterate 4 bytes each cycle
    j = 1
    for i in range(2, len(data_bytes) - 2, 4):
        # (byte5,3bits)<<16 | (byte4) << 8 | byte3
        spn = (((data_bytes[i+2] >> 5) & 0x7) << 16) | ((data_bytes[i+1] << 8) & 0xFF00) | data_bytes[i]
        fmi = data_bytes[i+2] & 0x1F # byte5, 5bits, Failure Module Indicator
        cm = (data_bytes[i+3] >> 7) & 0x01 # byte6, 1bit, Conversion Method
        oc = data_bytes[i+3] & 0x7F # #byte6, 7bits, Occurence Counter 
        if PRINT_DM1_PARSED:
            print(f"        DTC[{j}] -> SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}, CM: {cm}, OC: {oc}")
        j += 1

# Main function to read log file and print DTCs from individual frames or from BAM frames
def read_log_and_print_dtc(file_path):
    current_bams = []  # List to store current BAM messages

    with open(file_path, 'r') as file:
        for line in file:
            if 'Rx' in line:
                # Data that was split into multiple packets, concatenated and provided by the log itself under 'J1939TP'
                # printamos apenas para comparar com nossa logica de concatenacao
                if 'J1939TP FECAp' in line:  
                    if PRINT_J1939TP_FECAp:
                        print(line.strip())
                
                parts = line.split()
                message_id = parts[2]  # CAN ID
                src = message_id.zfill(8)[6:8] # source, last byte of CAN ID

                if(is_dm1_message_id(message_id)):
                    #Parse single FECA frame
                    data_bytes = [int(b, 16) for b in parts[6:14]]
                    spn = (((data_bytes[4] >> 5) & 0x7) << 16) | ((data_bytes[3] << 8) & 0xFF00) | data_bytes[2]
                    if(spn != 0):
                        if PRINT_DM1_SINGLE_FRAME:
                            print(line.strip())
                        timestamp = parts[0]
                        parse_dm1_message(timestamp, src, data_bytes)
                elif is_tp_cm_message_id(message_id):  # Identify BAM message
                    result = parse_tp_ct_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result

                        # If it is not DM1 (0xFECA), ignore it
                        if pgn != 65226: 
                            continue

                        # Replace 'EC' for 'EB' to obtain message_id_tp_ct
                        message_id_tp_ct = message_id.replace('EC', 'EB', 1)

                        # Remove older BAMs with the same message_id
                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)

                        # Add new BAM to the list
                        current_bams.append({
                            'timestamp': timestamp,
                            'message_id': message_id,
                            'message_id_tp_ct': message_id_tp_ct,
                            'total_size': total_size,
                            'num_packets': num_packets,
                            'pgn': pgn,
                            'packets': []
                        })
                        if PRINT_TP_CT:
                            print(f"TP.CT -> Time: {timestamp}, ID: {message_id}, Size: {total_size} bytes, Number of Packets: {num_packets}, PGN: {pgn:#X}")
                elif is_tp_dt_message_id(message_id):  # Identify TP.DT message
                    result = parse_tp_dt_message(line)
                    if result:
                        timestamp, message_id, packet_number, data = result
                        if PRINT_TP_DT:
                            print(f"TP.DT ->  Time: {timestamp}, ID: {message_id}, Packet Number: {packet_number}, Data: {' '.join(data)}")
                        
                        # Check if all packets were received
                        for bam in current_bams:
                            if bam['message_id_tp_ct'] == message_id:
                                if packet_number != (len(bam['packets']) + 1):
                                    if PRINT_INCORRET_ORDER:
                                        print('Packet Order is Incorrect')
                                    current_bams.remove(bam)
                                    break

                                bam['packets'].append((packet_number, data))
                                if len(bam['packets']) == bam['num_packets']:
                                    # Order packets by packet number
                                    bam['packets'].sort()
                                    combined_data = []
                                    for packet in bam['packets']:
                                        combined_data.extend(packet[1])
                                    # Limit the size of the combined data
                                    combined_data = combined_data[:bam['total_size']]

                                    if PRINT_TP_DM1_MULTI_FRAME:
                                        print(f"TP -> Time: {bam['timestamp']}, ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    
                                    # Converts string list to bytes list
                                    data_bytes = [int(b, 16) for b in combined_data]
                                    parse_dm1_message(timestamp, src, data_bytes)
                                    
                                    # Remove the parsed BAM from list
                                    current_bams.remove(bam)
                                    break

# Call the function with the path to the log file
# file_path = 'example_files/test.asc'
file_path = 'example_files/VWConstel2024_1.asc'
# file_path = 'example_files/VWConstel2024_2.asc'
read_log_and_print_dtc(file_path)
