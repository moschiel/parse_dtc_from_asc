import re
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk

file_path = 'example_files/VWConstel2024_1.asc'
# file_path = 'example_files/VWConstel2024_2.asc'

# Print control variables
PRINT_DM1_SINGLE_FRAME = False
PRINT_TP_CT = False
PRINT_TP_DT = False
PRINT_J1939TP_FECAp = False
PRINT_TP_DM1_MULTI_FRAME = False
PRINT_INCORRET_ORDER = False
PRINT_DM1_PARSED = False
PRINT_ACTIVE_DTCs = False
PRINT_NEW_ACTIVE_DTCs = False
PRINT_REMOVED_ACTIVE_DTCs = False
PRINT_REMOVED_CANDIDATE_DTCs = False

# Control variables for emulating time and display
EMULATE_TIME = True
DISPLAY_SCREEN = True
last_time = 0.0 

# List to store active faults
candidate_faults = []
active_faults = []
# Remove faults that have not been updated by this amount of time
debounce_fault_inactive = 20
debounce_fault_active_count = 10  # Number of occurrences to consider fault active
debounce_fault_active_time = 10  # Time window in seconds to consider fault active

# Variable to store the last displayed timestamp
last_displayed_timestamp = 0.0

# Flag to stop the thread
stop_thread = False

# Dictionary to store source descriptions
source_descriptions = {}

# Function to load source descriptions from file
def load_source_descriptions(file_path):
    global source_descriptions
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            source_descriptions[int(parts[0])] = parts[1]

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

def print_active_faults():
    if PRINT_ACTIVE_DTCs == False or EMULATE_TIME == False:
        return
    print(f'Active Faults:')
    global active_faults
    for fault in active_faults: 
        print(f"        SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}, MIL: {fault['mil']}, RSL: {fault['rsl']}, AWL: {fault['awl']}, PL: {fault['pl']}")

# Function to update the active faults list
def update_active_faults(src, spn, fmi, cm, oc, mil, rsl, awl, pl, float_timestamp):
    if EMULATE_TIME == False:
        return

    # Update if exist on list already
    global active_faults
    updatedExistingFault = False
    for fault in active_faults:
        if fault['src'] == src and fault['spn'] == spn and fault['fmi'] == fmi:
            fault['cm'] = cm
            fault['oc'] = oc
            fault['mil'] = mil
            fault['rsl'] = rsl
            fault['awl'] = awl
            fault['pl'] = pl
            fault['last_seen'] = float_timestamp
            if(fault['status'] == 'candidate'):
                fault['occurrences'] += 1
            updatedExistingFault = True

    # Add new candidate fault to the fault list
    if not updatedExistingFault:
        active_faults.append({
            'src': src,
            'spn': spn,
            'fmi': fmi,
            'cm': cm,
            'oc': oc,
            'mil': mil,
            'rsl': rsl,
            'awl': awl,
            'pl': pl,
            'last_seen': float_timestamp,
            'first_seen': float_timestamp,
            'occurrences': 1,
            'status': 'candidate'
        })
    
    # Verify if 'candidate' fault is elegible to become 'active'
    for fault in active_faults:
        if(fault['status'] == 'candidate'): # is candidate
            if((float_timestamp - fault['first_seen']) <= debounce_fault_active_time): # if debounce active timeout
                if(fault['occurrences'] >= debounce_fault_active_count): #if has the minimum amount of occurrences
                    fault['status'] = 'active' # set as active

        if PRINT_NEW_ACTIVE_DTCs:
            print(f'{float_timestamp} new fault SRC: 0x{src} ({int(src, 16)}), SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}')

    added_new_faults = not updatedExistingFault
    return added_new_faults

# Remove faults that have not been updated for a certain time
# or if they are not 'candidate' anymore
def remove_inactive_faults(float_timestamp):
    if EMULATE_TIME == False:
        return

    global active_faults
    global debounce_fault_inactive
    current_time = float_timestamp
    new_active_faults = []
    removed = False
    for fault in active_faults:
        if(fault['status'] == 'candidate'): # candidate fault, do not keep on list if it is not a candidate anymore
            if((float_timestamp - fault['first_seen']) <= debounce_fault_active_time):
                new_active_faults.append(fault)
            else:
                if PRINT_REMOVED_CANDIDATE_DTCs: 
                    print(f"{float_timestamp} removed CANDIDATE fault SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}")
                removed = True
        else: # active fault, do not keep on list if it is not active anymore
            if current_time - fault['last_seen'] <= debounce_fault_inactive:
                new_active_faults.append(fault)
            else:
                if PRINT_REMOVED_ACTIVE_DTCs: 
                    print(f"{float_timestamp} removed fault SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}")
                removed = True
    
    active_faults = new_active_faults
    if removed:
        update_active_faults_display()
        print_active_faults()

# Function to parse DM1 message
def parse_dm1_message(timestamp, src, data_bytes):
    mil = (data_bytes[0] >> 6) & 0x03  # byte1, 2bits, Malfunction Indicator Lamp status
    rsl = (data_bytes[0] >> 4) & 0x03  # byte1, 2bits, Red Stop Lamp status
    awl = (data_bytes[0] >> 2) & 0x03  # byte1, 2bits, Amber Warning Lamp status
    pl = data_bytes[0] & 0x03          # byte1, 2bits, Protect Lamp status
    rfu = data_bytes[1]                # byte2, reserved
    if PRINT_DM1_PARSED:
        print(f"DM1 -> Time: {timestamp}, SRC: 0x{src} ({int(src, 16)}), MIL: {mil}, RSL: {rsl}, AWL: {awl}, PL: {pl}")
    
    added_new_faults = False
    # Starting at third byte, iterate 4 bytes each cycle
    j = 1
    for i in range(2, len(data_bytes) - 2, 4):
        spn = (((data_bytes[i + 2] >> 5) & 0x7) << 16) | ((data_bytes[i + 1] << 8) & 0xFF00) | data_bytes[i]
        fmi = data_bytes[i + 2] & 0x1F  # byte5, 5bits, Failure Module Indicator
        cm = (data_bytes[i + 3] >> 7) & 0x01  # byte6, 1bit, Conversion Method
        oc = data_bytes[i + 3] & 0x7F  # byte6, 7bits, Occurrence Counter 
        if PRINT_DM1_PARSED:
            print(f"        DTC[{j}] -> SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}, CM: {cm}, OC: {oc}")
        
        if update_active_faults(src, spn, fmi, cm, oc, mil, rsl, awl, pl, float(timestamp)):
            added_new_faults = True
        j += 1

    update_active_faults_display()
    if added_new_faults:
        print_active_faults()

# Sleep to emulate log execution time
def emulate_waiting_time(float_timestamp):
    if EMULATE_TIME:
        global last_time
        if last_time != 0:
            time_diff = float_timestamp - last_time
            if time_diff > 0:
                time.sleep(time_diff)
        last_time = float_timestamp

def update_screen_time(float_timestamp):
    if EMULATE_TIME == False or DISPLAY_SCREEN == False:
        return
    global last_displayed_timestamp
    if float_timestamp - last_displayed_timestamp >= 1:
        last_displayed_timestamp = float_timestamp
        timestamp_label.config(text=f"Time: {int(float_timestamp)}s")
        percent = (float_timestamp / end_time) * 100
        progress_var.set(percent)
        root.update_idletasks()
        if(percent >= 100):
            global stop_thread
            stop_thread = True

# Function to get the end timestamp from the log file
def get_end_time(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in reversed(lines):
            if 'Rx' in line:
                parts = line.split()
                timestamp = float(parts[0])
                return timestamp
    return 0

# Main function to read log file and print DTCs from individual frames or from BAM frames
def read_log_and_print_dtc(file_path):
    current_bams = []  # List to store current BAM messages
    started_measurement = False

    with open(file_path, 'r') as file:
        for line in file:
            if stop_thread:
                break

            if started_measurement == False:
                if 'Start of measurement' in line:
                    started_measurement = True
                else:
                    continue

            parts = line.split()
            timestamp = parts[0]
            float_timestamp = float(timestamp)
            emulate_waiting_time(float_timestamp)
            update_screen_time(float_timestamp)
            
            if 'Rx' in line:
                if 'J1939TP FECAp' in line:  
                    if PRINT_J1939TP_FECAp:
                        print(line.strip())

                message_id = parts[2]  # CAN ID
                src = message_id.zfill(8)[6:8]  # source, last byte of CAN ID

                if is_dm1_message_id(message_id):
                    data_bytes = [int(b, 16) for b in parts[6:14]]
                    spn = (((data_bytes[4] >> 5) & 0x7) << 16) | ((data_bytes[3] << 8) & 0xFF00) | data_bytes[2]
                    if spn != 0:
                        if PRINT_DM1_SINGLE_FRAME:
                            print(line.strip())
                        parse_dm1_message(timestamp, src, data_bytes)
                elif is_tp_cm_message_id(message_id):  # Identify BAM message
                    result = parse_tp_ct_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result

                        if pgn != 65226:  # If it is not DM1 (0xFECA), ignore it
                            continue

                        message_id_tp_ct = message_id.replace('EC', 'EB', 1)

                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)

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
                        
                        for bam in current_bams:
                            if bam['message_id_tp_ct'] == message_id:
                                if packet_number != (len(bam['packets']) + 1):
                                    if PRINT_INCORRET_ORDER:
                                        print('Packet Order is Incorrect')
                                    current_bams.remove(bam)
                                    break

                                bam['packets'].append((packet_number, data))
                                if len(bam['packets']) == bam['num_packets']:
                                    bam['packets'].sort()
                                    combined_data = []
                                    for packet in bam['packets']:
                                        combined_data.extend(packet[1])
                                    combined_data = combined_data[:bam['total_size']]

                                    if PRINT_TP_DM1_MULTI_FRAME:
                                        print(f"TP -> Time: {bam['timestamp']}, ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    
                                    data_bytes = [int(b, 16) for b in combined_data]
                                    parse_dm1_message(timestamp, src, data_bytes)
                                    
                                    current_bams.remove(bam)
                                    break

                remove_inactive_faults(float_timestamp)

# Dictionary to store references to treeview items
treeview_items = {}
def update_active_faults_display():
    if EMULATE_TIME == False or DISPLAY_SCREEN == False:
        return

    global treeview_items

    current_fault_keys = {(fault['src'], fault['spn'], fault['fmi']) for fault in active_faults}

    for fault in active_faults:
        key = (fault['src'], fault['spn'], fault['fmi'])
        src_description = source_descriptions.get(int(fault['src'], 16), "")
        values = (
            f"0x{fault['src']} ({int(fault['src'], 16)}) - {src_description}", 
            f"0x{format(fault['spn'], 'X')} ({fault['spn']})", 
            fault['fmi'],
            fault['cm'], 
            fault['oc'], 
            fault['mil'], 
            fault['rsl'], 
            fault['awl'], 
            fault['pl'], 
            fault['last_seen'],
            fault['status']
        )

        tag = fault['status']

        if key in treeview_items:
            tree.item(treeview_items[key], values=values)
            tree.item(treeview_items[key], tags=(tag,))
        else:
            item_id = tree.insert('', 'end', values=values, tags=(tag,))
            treeview_items[key] = item_id

    for key in list(treeview_items.keys()):
        if key not in current_fault_keys:
            values = tree.item(treeview_items[key], 'values')
            tree.item(treeview_items[key], values=(*values[:-1], 'inactive'))
            tree.item(treeview_items[key], tags=('inactive',))

# Load source descriptions at the start
load_source_descriptions('sources.txt')

if EMULATE_TIME and DISPLAY_SCREEN:
    root = tk.Tk()
    root.title("Active Faults")
    root.geometry("900x400")

    columns = ('SRC', 'SPN', 'FMI', 'CM', 'OC', 'MIL', 'RSL', 'AWL', 'PL', 'Last Seen', 'Status')
    tree = ttk.Treeview(root, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=80)
    tree.pack(fill=tk.BOTH, expand=True)
    
    tree.tag_configure('active', background='lightgreen')
    tree.tag_configure('inactive', background='lightgrey')
    tree.tag_configure('candidate', background='white')

    timestamp_label = tk.Label(root, text="Time: 0s")
    timestamp_label.pack()

    debounce_inactive_label = tk.Label(root, text="Debounce Fault Inactive (seconds):")
    debounce_inactive_label.pack()
    debounce_inactive_entry = tk.Entry(root)
    debounce_inactive_entry.pack()
    debounce_inactive_entry.insert(0, str(debounce_fault_inactive))

    debounce_active_count_label = tk.Label(root, text="Debounce Fault Active Count:")
    debounce_active_count_label.pack()
    debounce_active_count_entry = tk.Entry(root)
    debounce_active_count_entry.pack()
    debounce_active_count_entry.insert(0, str(debounce_fault_active_count))

    debounce_active_time_label = tk.Label(root, text="Debounce Fault Active Time (seconds):")
    debounce_active_time_label.pack()
    debounce_active_time_entry = tk.Entry(root)
    debounce_active_time_entry.pack()
    debounce_active_time_entry.insert(0, str(debounce_fault_active_time))

    def update_configs():
        global debounce_fault_inactive, debounce_fault_active_count, debounce_fault_active_time
        try:
            debounce_fault_inactive = float(debounce_inactive_entry.get())
            debounce_fault_active_count = int(debounce_active_count_entry.get())
            debounce_fault_active_time = float(debounce_active_time_entry.get())
        except ValueError:
            pass

    configs_button = tk.Button(root, text="Update Configs", command=update_configs)
    configs_button.pack()

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
    progress_bar.pack(fill=tk.X, expand=True)

    end_time = get_end_time(file_path)

    def read_log_thread(file_path):
        read_log_and_print_dtc(file_path)
        root.quit()

    threading.Thread(target=read_log_thread, args=(file_path,)).start()

    def on_closing():
        global stop_thread
        stop_thread = True
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
else:
    read_log_and_print_dtc(file_path)
