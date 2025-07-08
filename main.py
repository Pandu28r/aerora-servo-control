import os
import time
import psutil
import statistics
import csv
import threading
import platform
from dynamixel_sdk import *
import customtkinter as ctk
from datetime import datetime
from lib_aerora import Aerora
import tkinter.messagebox as messagebox

if platform.system() == "Windows":
    DEVICENAME = 'COM6'
elif platform.system() == "Linux":
    DEVICENAME = '/dev/ttyUSB0'
else:  # macOS
    DEVICENAME = '/dev/cu.usbserial-*'

# Configuration constants
PROTOCOL_VERSION = 2.0
ADDR_TORQUE_ENABLE_XL320 = 24
ADDR_GOAL_POSITION_XL320 = 30
ADDR_PRESENT_POSITION_XL320 = 37
ADDR_MOVING_SPEED_XL320 = 32
ADDR_MOVNG_XL320 = 49

ADDR_TORQUE_ENABLE_XM430 = 64
ADDR_GOAL_POSITION_XM430 = 116
ADDR_PRESENT_POSITION_XM430 = 132
ADDR_PROFILE_VELOCITY_XM430 = 112
ADDR_MOVNG_XM430 = 122

BAUDRATE = 1000000
TORQUE_ENABLE = 1
TORQUE_DISABLE = 0
DXL_MOVING_STATUS_THRESHOLD = 10
READ_TIMEOUT_MS = 150
COMMUNICATION_DELAY = 0.01

portHandler = None
packetHandler = None
groupSyncWrite_XL320 = None
groupSyncRead_XL320 = None
groupSyncWrite_XM430 = None
groupSyncRead_XM430 = None
groupSyncReadMove_XL320 = None
groupSyncReadMove_XM430 = None

connection_status = False
health_check_counter = 0
is_pause = False
is_stop = False
is_gerak = False
step = 0
data_frame = []
data_hasil = []
consecutive_failures = 0

DXL_ALL = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]
DXL_XL320 = [0,1,2,3,4,5,6,7,8,9,10,11,12]
DXL_XM430 = [13,14,15,16,17,18,19,20,21,22,23,24,25,26]

data_hasil = []

num_servos = len(DXL_ALL)

###################
#    Dynamixel    #
###################

def servo_clear_write_param():
    groupSyncWrite_XL320.clearParam()
    groupSyncWrite_XM430.clearParam()

def servo_clear_read_param():
    groupSyncRead_XL320.clearParam()
    groupSyncRead_XM430.clearParam()

def servo_clear_all_param():
    servo_clear_write_param()
    servo_clear_read_param()

def servo_torque_enable():
    servo_found = False
    failed_servos = []
    for id in DXL_ALL:
        if id in DXL_XL320:
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, id, ADDR_TORQUE_ENABLE_XL320, TORQUE_ENABLE)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                print(f"[ERROR] Gagal enable torque ID:{id} - Comm: {dxl_comm_result}, Error: {dxl_error}")
                failed_servos.append(id)
            else:
                servo_found = True
        elif id in DXL_XM430:
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, id, ADDR_TORQUE_ENABLE_XM430, TORQUE_ENABLE)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                print(f"[ERROR] Gagal enable torque ID:{id} - Comm: {dxl_comm_result}, Error: {dxl_error}")
                failed_servos.append(id)
            else:
                servo_found = True
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")

    return servo_found, failed_servos

def servo_torque_disable():
    servo_found = False
    failed_servos = []
    for id in DXL_ALL:
        if id in DXL_XL320:
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, id, ADDR_TORQUE_ENABLE_XL320, TORQUE_DISABLE)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                print(f"[ERROR] Gagal disable torque ID:{id} - Comm: {dxl_comm_result}, Error: {dxl_error}")
                failed_servos.append(id)
            else:
                servo_found = True
        elif id in DXL_XM430:
            dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, id, ADDR_TORQUE_ENABLE_XM430, TORQUE_DISABLE)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                print(f"[ERROR] Gagal disable torque ID:{id} - Comm: {dxl_comm_result}, Error: {dxl_error}")
                failed_servos.append(id)
            else:
                servo_found = True
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")

    return servo_found, failed_servos

def servo_groupsync_get_data():
    stat_get = True
    for id in DXL_ALL:
        if id in DXL_XL320:
            if not groupSyncRead_XL320.isAvailable(id, ADDR_PRESENT_POSITION_XL320, 2):
                print(f"    [READ] Data not available for servo {id}")
                stat_get = False
        elif id in DXL_XM430:
            if not groupSyncRead_XM430.isAvailable(id, ADDR_PRESENT_POSITION_XM430, 4):
                print(f"    [READ] Data not available for servo {id}")
                stat_get = False
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")

    positions = []
    for id in DXL_ALL:
        if id in DXL_XL320:
            present_pos = groupSyncRead_XL320.getData(id, ADDR_PRESENT_POSITION_XL320, 2)
            positions.append(round(Aerora.map(present_pos, 0, 1023, 0, 300)))
        elif id in DXL_XM430:
            present_pos = groupSyncRead_XM430.getData(id, ADDR_PRESENT_POSITION_XM430, 4)
            positions.append(round(Aerora.map(present_pos, 0, 4096, 0, 360)))
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")
    return stat_get, positions

def servo_groupsync_add_param():
    for id in DXL_ALL:
        if id in DXL_XL320:
            if not groupSyncRead_XL320.addParam(id):
                print(f"[ERROR] Failed to add servo ID:{id} to GroupSyncRead")
                return False, id
        elif id in DXL_XM430:
            if not groupSyncRead_XM430.addParam(id):
                print(f"[ERROR] Failed to add servo ID:{id} to GroupSyncRead")
                return False, id
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")
    return True, -1

def servo_groupsync_move_add_param():
    groupSyncReadMove_XL320.clearParam()
    groupSyncReadMove_XM430.clearParam()

    for id in DXL_ALL:
        if id in DXL_XL320:
            if not groupSyncReadMove_XL320.addParam(id):
                print(f"[ERROR] Failed to add servo ID:{id} to GroupSyncReadMove")
                return False, id
        elif id in DXL_XM430:
            if not groupSyncReadMove_XM430.addParam(id):
                print(f"[ERROR] Failed to add servo ID:{id} to GroupSyncReadMove")
                return False, id
        else:
            print(f"id: {id} tidak ada dalam XL320 atau XM430")
    return True, -1

def servo_groupsync_read_execute():
    dxl_comm_result = groupSyncRead_XL320.txRxPacket()
    if dxl_comm_result != COMM_SUCCESS:
        print(f"    [READ] GroupSyncRead XL320 txRxPacket failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
        return False
    dxl_comm_result = groupSyncRead_XM430.txRxPacket()
    if dxl_comm_result != COMM_SUCCESS:
        print(f"    [READ] GroupSyncRead XM430 txRxPacket failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
        return False
    return True

def servo_connect():
    global portHandler, packetHandler
    try:
        portHandler = PortHandler(DEVICENAME)
        packetHandler = PacketHandler(PROTOCOL_VERSION)
        if not Aerora.check_port_exists(DEVICENAME):
            raise Exception(f"Port {DEVICENAME} tidak ditemukan.")

        if not portHandler.openPort():
            raise Exception(f"Gagal membuka port {DEVICENAME}. Pastikan device terhubung dan port tidak digunakan aplikasi lain.")

        print("Port berhasil dibuka")

        # Set baudrate
        if not portHandler.setBaudRate(BAUDRATE):
            portHandler.closePort()
            raise Exception(f"Gagal mengatur baudrate ke {BAUDRATE}")

        print("Baudrate berhasil diset")

        # Test koneksi dengan ping servo dengan timeout
        servo_found = False
        failed_servos = []

        servo_found, failed_servos = servo_torque_enable()

        if not servo_found:
            portHandler.closePort()
            raise Exception(f"Tidak ada servo yang merespons pada port {DEVICENAME}.\nServo yang dicoba: {DXL_ALL}\nPastikan servo terhubung dan dikonfigurasi dengan benar.")

        success_msg = f"Koneksi berhasil ke port {DEVICENAME}!"
        if failed_servos:
            fail_msg = f"Catatan: Servo {failed_servos} tidak merespons."
            return False, fail_msg
        return True, success_msg

    except Exception as e:
        message = str(e)
        # Pastikan port ditutup jika terjadi error
        if portHandler:
            try:
                portHandler.closePort()
            except:
                pass
        if message.split()[0] == 'could':
            message = f"Gagal membuka port {DEVICENAME}. Pastikan device terhubung dan port tidak digunakan aplikasi lain."
        return False, message

def servo_init_groupsync():
    global groupSyncRead_XL320, groupSyncRead_XM430, groupSyncWrite_XL320, groupSyncWrite_XM430
    print(f"=== {num_servos} SERVO GROUPSYNC INITIALIZATION ===")

    groupSyncWrite_XL320 = GroupSyncWrite(portHandler, packetHandler, ADDR_GOAL_POSITION_XL320, 4)
    groupSyncRead_XL320 = GroupSyncRead(portHandler, packetHandler, ADDR_PRESENT_POSITION_XL320, 2)
    groupSyncWrite_XM430 = GroupSyncWrite(portHandler, packetHandler, ADDR_PROFILE_VELOCITY_XM430, 8)
    groupSyncRead_XM430 = GroupSyncRead(portHandler, packetHandler, ADDR_PRESENT_POSITION_XM430, 4)

    servo_clear_all_param()

    status, id_servo = servo_groupsync_add_param()
    if not status:
        print(f"[ERROR] Failed to add servo ID:{id_servo} to GroupSyncRead")
        return False

    if not servo_groupsync_read_execute():
        return False

    potitions = servo_groupsync_get_data()
    print('[INFO] Berhasil inisialisasi groupsync')
    print(potitions)
    return True

def servo_init_timeout():
    global groupSyncReadMove_XL320, groupSyncReadMove_XM430
    groupSyncReadMove_XL320 = GroupSyncRead(portHandler, packetHandler, ADDR_MOVNG_XL320,1)
    groupSyncReadMove_XM430 = GroupSyncRead(portHandler, packetHandler, ADDR_MOVNG_XM430,1)

    servo_groupsync_move_add_param()

    return servo_check_timeout()

def servo_setup_ready_position():
    global groupSyncReadMove_XM430, groupSyncReadMove_XL320
    # FIX 1: Set proper packet timeout for high baudrate
    portHandler.setPacketTimeout(READ_TIMEOUT_MS)
    print(f"[CONFIG] Packet timeout set to {READ_TIMEOUT_MS}ms")

    print("[WRITE] Setup posisi siap...")
    servo_clear_write_param()
    for dxl_id in DXL_ALL:
        time.sleep(0.01)
        goal_pos =  [150, 149, 167, 173, 141, 154, 154, 148, 156, 146, 149, 163, 152, 176, 176, 180, 181, 179, 174, 252, 105, 37, 321, 111, 249, 179, 174]
        if dxl_id < 13:
            goal_poss = round(Aerora.map(float(goal_pos[dxl_id]), 0, 300, 0, 1023))
            if dxl_id == 3 or dxl_id == 4:
                goal_time = 50
            else:
                goal_time = 200
            param_goal_position = [DXL_LOBYTE(DXL_LOWORD(int(goal_poss))), DXL_HIBYTE(DXL_LOWORD(int(goal_poss))),DXL_LOBYTE(DXL_LOWORD(int(goal_time))), DXL_HIBYTE(DXL_LOWORD(int(goal_time)))]
            if not groupSyncWrite_XL320.addParam(dxl_id, param_goal_position):
                print(f"    [WRITE] Failed to add param for servo {dxl_id}")
                return False
        else:
            goal_poss = round(Aerora.map(float(goal_pos[dxl_id]), 0, 360, 0, 4096))
            goal_time = 2100
            param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_time)), DXL_HIBYTE(DXL_LOWORD(goal_time)), DXL_LOBYTE(DXL_HIWORD(goal_time)), DXL_HIBYTE(DXL_HIWORD(goal_time)),DXL_LOBYTE(DXL_LOWORD(goal_poss)), DXL_HIBYTE(DXL_LOWORD(goal_poss)), DXL_LOBYTE(DXL_HIWORD(goal_poss)), DXL_HIBYTE(DXL_HIWORD(goal_poss))]
            if not groupSyncWrite_XM430.addParam(dxl_id, param_goal_position):
                print(f"    [WRITE] Failed to add param for servo {dxl_id}")
                return False

        portHandler.clearPort()
        time.sleep(0.005)

    dxl_comm_result = groupSyncWrite_XL320.txPacket()
    if dxl_comm_result != COMM_SUCCESS:
        print(f"    [WRITE] GroupSyncWrite XL320 failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
        return False

    dxl_comm_result = groupSyncWrite_XM430.txPacket()
    if dxl_comm_result != COMM_SUCCESS:
        print(f"    [WRITE] GroupSyncWrite XM430 failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
        return False

    time.sleep(4)

    if not 	servo_init_timeout():
        return False

    print(f"[OK] Perfect initialization completed for {num_servos} servos")

    return True

def servo_disconnect():
    servo_torque_disable()

    try:
        if portHandler:
            portHandler.closePort()
            print("Port berhasil ditutup")
        return True, "Disconnected successfully!"
    except Exception as e:
        return True, f"Disconnected (with warning: {str(e)})"  # Return True karena disconnect tetap berhasil

def servo_health_check():
    global health_check_counter
    health_check_counter += 1
    if health_check_counter % 10 != 0:
        return True

    healthy = True
    for dxl_id in DXL_ALL:
        portHandler.clearPort()
        if dxl_id < 13:
            _, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION_XL320)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                healthy = False
                break
        else:
            _, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION_XM430)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                healthy = False
                break

        time.sleep(0.005)
    return healthy

def servo_check_timeout():
    dxl_comm_result = groupSyncReadMove_XL320.txRxPacket()
    if dxl_comm_result != COMM_SUCCESS:
        # print("%s" % packetHandler.getTxRxResult(dxl_comm_result),"xlmove")
        return False
    dxl_comm_result = groupSyncReadMove_XM430.txRxPacket()
    if dxl_comm_result != COMM_SUCCESS:
        # print("%s" % packetHandler.getTxRxResult(dxl_comm_result),"xmmove")
        return False

    dxl_present_condition_xl320 = []
    dxl_present_condition_xm430 = []
    for id in DXL_ALL:
        if id in DXL_XL320:
            dxl_present_condition_xl320.append(groupSyncReadMove_XL320.getData(id, ADDR_MOVNG_XL320, 1))
        elif id in DXL_XM430:
            dxl_present_condition_xm430.append(groupSyncReadMove_XL320.getData(id, ADDR_MOVNG_XM430, 1))

    dxl_present_condition_all = dxl_present_condition_xl320 + dxl_present_condition_xm430
    return all(x == 0 for x in dxl_present_condition_all)

def servo_recover_communication():
    global groupSyncRead_XL320, groupSyncRead_XM430, groupSyncWrite_XL320, groupSyncWrite_XM430
    global consecutive_failures
    print("    [RECOVERY] Attempting communication recovery...")

    # FIX 5: Proper recovery sequence
    portHandler.clearPort()
    time.sleep(0.1)

    # Clear and reinitialize GroupSync objects
    servo_clear_all_param()

    # Reinitialize with fresh objects
    groupSyncWrite_XL320 = GroupSyncWrite(portHandler, packetHandler, ADDR_GOAL_POSITION_XL320, 4)
    groupSyncRead_XL320 = GroupSyncRead(portHandler, packetHandler, ADDR_PRESENT_POSITION_XL320, 2)

    groupSyncWrite_XM430 = GroupSyncWrite(portHandler, packetHandler, ADDR_PROFILE_VELOCITY_XM430, 8)
    groupSyncRead_XM430 = GroupSyncRead(portHandler, packetHandler, ADDR_PRESENT_POSITION_XM430, 4)

    recovery_success = True
    recovery_success = servo_groupsync_add_param()

    if recovery_success:
        consecutive_failures = 0
        print("    [RECOVERY] Communication recovery successful")
    else:
        print("    [RECOVERY] Communication recovery failed")

    return recovery_success

####################
#      Motion      #
####################

def motion_create_data_structure(iterasi, method):
    if method == 0:
        metode = "NONGROUP"
    elif method == 1:
        metode = "GROUPSYNC"
    else:
        metode = "GROUPSYNC"
    """Create dynamic data structure based on number of servos"""
    data_iterasi = {
        'metode': f'{metode}_{num_servos}_SERVO',
        'iterasi': iterasi,
        'servo_ids': DXL_ALL.copy(),
        'waktu_operasi': [],
        'waktu_write': [],
        'waktu_read': [],
        'error_count': 0,
        'success_read': 0,
        'read_try' : 0,
        'recovery_count': 0,
        'cpu_usage_start': 0,
        'cpu_usage_end': 0,
        'memory_usage': 0
    }

    for i in range(num_servos):
        data_iterasi[f'error_akhir_servo_{i}'] = []
        data_iterasi[f'status_servo_{i}'] = []

    return data_iterasi

def motion_write_groupsync_robust(gerakan):
    max_retries = 2
    write_start = time.perf_counter()
    for retry in range(max_retries):
        success_add = True
        groupSyncWrite_XL320.clearParam()
        groupSyncWrite_XM430.clearParam()
        for i, dxl_id in enumerate(DXL_IDS):
            if dxl_id in DXL_XL320:
                goal_pos = round(Aerora.map(int(DXL_DEGREE[i]), 0, 300, 0, 1023))
                goal_time = int(MOTION_TIME_XL320[gerakan][dxl_id])
                param_goal_position = [DXL_LOBYTE(DXL_LOWORD(int(goal_pos))), DXL_HIBYTE(DXL_LOWORD(int(goal_pos))),DXL_LOBYTE(DXL_LOWORD(int(goal_time))), DXL_HIBYTE(DXL_LOWORD(int(goal_time)))]
                if not groupSyncWrite_XL320.addParam(dxl_id, param_goal_position):
                    success_add = False
                    print(f"    [WRITE] Failed to add param for servo {dxl_id}")
            elif dxl_id in DXL_XM430:
                goal_pos = round(Aerora.map(int(DXL_DEGREE[i]), 0, 360, 0, 4096))
                goal_time = int(MOTION_TIME_XM430[gerakan][dxl_id - 13])
                param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_time)), DXL_HIBYTE(DXL_LOWORD(goal_time)), DXL_LOBYTE(DXL_HIWORD(goal_time)), DXL_HIBYTE(DXL_HIWORD(goal_time)),DXL_LOBYTE(DXL_LOWORD(goal_pos)), DXL_HIBYTE(DXL_LOWORD(goal_pos)), DXL_LOBYTE(DXL_HIWORD(goal_pos)), DXL_HIBYTE(DXL_HIWORD(goal_pos))]
                if not groupSyncWrite_XM430.addParam(dxl_id, param_goal_position):
                    success_add = False
                    print(f"    [WRITE] Failed to add param for servo {dxl_id}")
            else:
                print(f"    [WRITE] Failed to add param for servo {dxl_id}")
                success_add = False

        if success_add:
            portHandler.clearPort()
            time.sleep(0.005)

            dxl_comm_result = groupSyncWrite_XL320.txPacket()
            if dxl_comm_result == COMM_SUCCESS:
                xl_320 = True
            else:
                print(f"    [WRITE] GroupSyncWrite XL320 failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
                xl_320 = False

            dxl_comm_result = groupSyncWrite_XM430.txPacket()
            if dxl_comm_result == COMM_SUCCESS:
                if xl_320:
                    write_time = (time.perf_counter() - write_start) * 1000
                    time.sleep(COMMUNICATION_DELAY)
                    return write_time, True
            else:
                print(f"    [WRITE] GroupSyncWrite XM430 failed: {packetHandler.getTxRxResult(dxl_comm_result)}")

        if retry < max_retries - 1:
            time.sleep(0.02 * (retry + 1))

    return 0, False

def motion_read_groupsync_robust():
    read_start = time.perf_counter()
    positions = []
    success = True

    time.sleep(0.01)

    if not servo_groupsync_read_execute():
        return [], 0, False

    success, positions = servo_groupsync_get_data()

    if not success:
        return [], 0, False

    read_time = (time.perf_counter() - read_start) * 1000
    return positions, read_time, True

def motion_retry_write_speed(servos, gerakan):
    failed_servos = []
    success = True
    for dxl_id in servos:
        if dxl_id in DXL_XL320:
            goal_time = int(MOTION_TIME_XL320[gerakan][dxl_id])
            dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, ADDR_MOVING_SPEED_XL320, goal_time)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                success = False
                print(f"    [WRITE] Failed to write for servo {dxl_id}")
                failed_servos.append(dxl_id)
        elif dxl_id in DXL_XM430:
            goal_time = int(MOTION_TIME_XM430[gerakan][dxl_id - 13])
            dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, dxl_id, ADDR_PROFILE_VELOCITY_XM430, goal_time)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                success = False
                print(f"    [WRITE] Failed to write for servo {dxl_id}")
                failed_servos.append(dxl_id)
        else:
            print(f"    [WRITE] Servo {dxl_id} cannot be found in XL320 and XM430")
            success = False
        time.sleep(COMMUNICATION_DELAY)

        return success, failed_servos

def motion_retry_write_degree(servos, indexes):
    failed_servos = []
    success = True
    for i, id in enumerate(servos):
        if id in DXL_XL320:
            goal_pos = DXL_DEGREE[indexes[i]]
            dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, id, ADDR_GOAL_POSITION_XL320, goal_pos)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                success = False
                print(f"    [WRITE] Failed to write for servo {id}")
                failed_servos.append(id)
        elif id in DXL_XM430:
            goal_pos = DXL_DEGREE[indexes[i]]
            dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, id, ADDR_GOAL_POSITION_XM430, goal_pos)
            if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                success = False
                print(f"    [WRITE] Failed to write for servo {id}")
                failed_servos.append(id)
        else:
            print(f"    [WRITE] Servo {id} cannot be found in XL320 and XM430")
            success = False
        time.sleep(COMMUNICATION_DELAY)

        return success, failed_servos

def motion_write_nongroupsync_robust(gerakan):
    max_retries = 2  # Reduced retries for faster recovery

    for retry in range(max_retries):
        if retry >= 1:
            if failed_servos_speed:
                motion_retry_write_speed(failed_servos_speed, gerakan)
            if failed_servo_degree:
                motion_retry_write_degree(failed_servo_degree, indexes)

            if success:
                write_time = (time.perf_counter() - write_start) * 1000
                time.sleep(COMMUNICATION_DELAY * 2)
                return write_time, True

            if retry < max_retries - 1:
                print(f"    [RETRY] Write speed failed for servos {failed_servos_speed} and write degree failed for servo {failed_servo_degree}, attempt {retry + 1}/{max_retries}")
                time.sleep(0.02 + (retry * 0.01))

            continue

        write_start = time.perf_counter()
        success = True
        indexes = []
        failed_servos_speed = []
        failed_servo_degree = []

        for i, dxl_id in enumerate(DXL_IDS):
            if dxl_id in DXL_XL320:
                goal_time = int(MOTION_TIME_XL320[gerakan][dxl_id])
                dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, ADDR_MOVING_SPEED_XL320, goal_time)
                if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                    success = False
                    print(f"    [WRITE] Failed to write for servo {dxl_id}")
                    failed_servos_speed.append(dxl_id)
            elif dxl_id in DXL_XM430:
                goal_time = int(MOTION_TIME_XM430[gerakan][dxl_id - 13])
                dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, dxl_id, ADDR_PROFILE_VELOCITY_XM430, goal_time)
                if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                    success = False
                    print(f"    [WRITE] Failed to write for servo {dxl_id}")
                    failed_servos_speed.append(dxl_id)
            else:
                print(f"    [WRITE] Servo {dxl_id} cannot be found in XL320 and XM430")
                success = False
            time.sleep(COMMUNICATION_DELAY)

        for i, dxl_id in enumerate(DXL_IDS):
            if dxl_id in DXL_XL320:
                goal_pos = round(Aerora.map(int(DXL_DEGREE[i]), 0, 300, 0, 1023))
                dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, dxl_id, ADDR_GOAL_POSITION_XL320, goal_pos)
                if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                    success = False
                    print(f"    [WRITE] Failed to write for servo {dxl_id}")
                    indexes.append(i)
                    failed_servo_degree.append(dxl_id)
            elif dxl_id in DXL_XM430:
                goal_pos = round(Aerora.map(int(DXL_DEGREE[i]), 0, 360, 0, 4096))
                dxl_comm_result, dxl_error = packetHandler.write4ByteTxRx(portHandler, dxl_id, ADDR_GOAL_POSITION_XM430, goal_pos)
                if dxl_comm_result != COMM_SUCCESS or dxl_error != 0:
                    success = False
                    print(f"    [WRITE] Failed to write for servo {dxl_id}")
                    indexes.append(i)
                    failed_servo_degree.append(dxl_id)
            else:
                print(f"    [WRITE] Servo {dxl_id} cannot be found in XL320 and XM430")
                success = False
            time.sleep(COMMUNICATION_DELAY)

        if success:
            write_time = (time.perf_counter() - write_start) * 1000
            time.sleep(COMMUNICATION_DELAY * 2)
            return write_time, True

        if retry < max_retries - 1:
            print(f"    [RETRY] Write speed failed for servos {failed_servos_speed} and write degree failed for servo {failed_servo_degree}, attempt {retry + 1}/{max_retries}")
            time.sleep(0.02 + (retry * 0.01))

    return 0, False

def motion_read_nongroupsync_robust():
    max_retries = 1
    servo = DXL_ALL
    positions = []
    indexes = list(range(len(DXL_ALL)))
    for retry in range(max_retries):
        read_start = time.perf_counter()
        success = True
        if retry > 0:
            servo = failed_servos
            indexes = failed_index
        failed_servos = []
        failed_index = []

        for i, dxl_id in enumerate(servo):
            if dxl_id in DXL_XL320:
                present_pos, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION_XL320)
                if dxl_comm_result == COMM_SUCCESS and dxl_error == 0:
                    positions.insert(indexes[i], round(Aerora.map(present_pos, 0, 1023, 0, 300)))
                else:
                    failed_servos.append(dxl_id)
                    failed_index.append(indexes[i])
                    success = False
            elif dxl_id in DXL_XM430:
                present_pos, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION_XM430)
                if dxl_comm_result == COMM_SUCCESS and dxl_error == 0:
                    positions.insert(indexes[i], round(Aerora.map(present_pos, 0, 4096, 0, 360)))
                else:
                    failed_servos.append(dxl_id)
                    failed_index.append(indexes[i])
                    success = False
            time.sleep(0.01)

        if success:
            read_time = (time.perf_counter() - read_start) * 1000
            return positions, read_time, True

        if retry < max_retries - 1:
            time.sleep(0.01 + (retry * 0.005))

    return [], 0, False

def motion_run_groupsync():
    global DXL_IDS, DXL_DEGREE, DXL_DEGREE_XL320, DXL_DEGREE_XM430
    global data_hasil, is_pause, is_stop, step, is_gerak, data_frame, data_hasil, consecutive_failures

    print("mulai group")
    print(step)
    # Process each movement frame from the motion data
    for frame_index in range(len(MOTION_DXL)):
        if is_stop or is_pause:
            if is_pause:
                step = frame_index
            break
        print(frame_index)
        if frame_index < step:
            continue

        is_gerak = True
        print(f"[RUN] Gerakan Frame {frame_index + 1}/{len(MOTION_DXL)}")
        move_label.configure(text=f"Gerakan {frame_index + 1}/{len(MOTION_DXL)}")
        # Health check before processing frame
        if not servo_health_check():
            if not servo_recover_communication():
                print("[ERROR] Critical failure - stopping test")
                break

        # Extract servo data for current frame
        DXL_IDS = Aerora.getIndexByNotElement(MOTION_DXL[frame_index], "-1")
        DXL_DEGREE = Aerora.getNotValue(MOTION_DXL[frame_index], "-1")
        DXL_DEGREE_XL320, DXL_DEGREE_XM430 = Aerora.getNotValue_v2(MOTION_DXL[frame_index], "-1")

        print(f"[FRAME] Active servos: {DXL_IDS}")
        print(f"[FRAME] Target positions: {DXL_DEGREE}")

        # Create data structure for current frame
        data_frame = motion_create_data_structure(frame_index + 1, 1)

        # Get system resources info
        process = psutil.Process()
        data_frame['cpu_usage_start'] = process.cpu_percent()
        data_frame['memory_usage'] = process.memory_info().rss / 1024 / 1024

        # Execute movement for current frame
        operation_start = time.perf_counter()

        # Write positions to servos
        write_time, write_success = motion_write_groupsync_robust(frame_index)

        if not write_success:
            data_frame['error_count'] += 1
            consecutive_failures += 1
            if consecutive_failures >= 5:
                if servo_recover_communication():
                    data_frame['recovery_count'] += 1
                    consecutive_failures = 0
                    write_time, write_success = motion_write_groupsync_robust(frame_index)
            if not write_success:
                print("    [ERROR] Write gagal setelah recovery")
                continue

        data_frame['waktu_write'] = write_time
        print(f"    [WRITE] waktu: {write_time:.2f} ms")

        # Wait for servo movement
        time.sleep(0.15)

        # Monitor servo movement until target reached
        cycle_count = 0
        final_positions = None
        consecutive_read_failures = 0
        recovery = 0
        timeout = 0
        success_read = 0
        while True:
            positions, read_time, read_success = motion_read_groupsync_robust()
            if not read_success:
                consecutive_read_failures += 1
                data_frame['error_count'] += 1
                consecutive_failures += 1

                if recovery >= 10:
                    final_positions = None
                    break

                if consecutive_read_failures >= 5:
                    print("    [WARNING] Multiple consecutive read failures")
                    if servo_recover_communication():
                        data_frame['recovery_count'] += 1
                        cycle_count += 1
                        consecutive_read_failures = 0
                        recovery += 1
                        continue
                    else:
                        print("    [ERROR] Recovery failed - aborting cycle")
                        break
                time.sleep(0.03)
                cycle_count += 1
                continue

            success_read += 1
            cycle_count += 1
            consecutive_read_failures = 0
            consecutive_failures = 0
            data_frame['waktu_read'] = read_time

            # Check if servos reached target positions
            servos_at_target = 0
            position_errors = []

            for i, servo_id in enumerate(DXL_IDS):
                servo_index = DXL_ALL.index(servo_id)
                present_pos = positions[servo_index]
                goal_pos = DXL_DEGREE[i]
                error = abs(goal_pos - present_pos)
                position_errors.append(error)
                if error <= DXL_MOVING_STATUS_THRESHOLD:
                    servos_at_target += 1

            if cycle_count % 20 == 0 and cycle_count > 0:
                print(f"    [PROGRESS] Cycle {cycle_count}: {servos_at_target}/{len(DXL_IDS)} servos at target")
                print(f"    [ERRORS] Current position errors: {position_errors}")

            if servos_at_target == len(DXL_IDS):
                final_positions = positions[:]
                print(f"    [TARGET] tercapai pada cycle {cycle_count}")
                is_gerak = False
                break

            if servo_check_timeout():

                final_positions = positions[:]
                timeout += 1
                print(f"    [TIMEOUT] Position tidak tercapai dan servo tidak bergerak: {position_errors}")
                print("     [INFO] Gerakan dilanjutkan")
                is_gerak = False
                break

            time.sleep(0.025)

        # Record results for current frame
        if final_positions is not None:
            for i, servo_id in enumerate(DXL_IDS):
                servo_index = DXL_ALL.index(servo_id)
                present_pos = final_positions[servo_index]
                goal_pos = DXL_DEGREE[i]
                error_pos = abs(goal_pos - present_pos)

                servo_key_error = f'error_akhir_servo_{servo_index}'
                servo_key_status = f'status_servo_{servo_index}'
                data_frame[servo_key_error].append(error_pos)
                data_frame[servo_key_status].append(error_pos <= DXL_MOVING_STATUS_THRESHOLD)

            operation_time = (time.perf_counter() - operation_start) * 1000
            data_frame['waktu_operasi'] = operation_time
            print(f"    [OPERATION] waktu total: {operation_time:.2f} ms")
        else:
            print("    [TIMEOUT] Read tidak berhasil membaca")
            timeout += 1
            if 'positions' in locals():
                print(f"    [DEBUG] Last known positions: {positions}")
            print(f"    [DEBUG] Target positions: {DXL_DEGREE}")

        # Update system resource usage
        data_frame['cpu_usage_end'] = process.cpu_percent()
        data_frame['success_read'] = success_read
        data_frame['read_try'] = cycle_count
        data_frame['timeout'] = timeout
        data_hasil.append(data_frame)

        # Print frame results
        print(f"[RESULT] Recoveries: {data_frame['recovery_count']}, Errors: {data_frame['error_count']}")
        print(f"[RESULT] Write Time: {data_frame['waktu_write']} ms")
        print(f"[RESULT] Read Time: {data_frame['waktu_read']}  ms")

        # Wait before next frame (if not last frame)
        if frame_index < len(MOTION_DXL) - 1:
            print("[INFO] Waiting before next frame...")
            time.sleep(0.1)

    if (frame_index+1) >= len(MOTION_DXL) or is_stop:
        if (frame_index+1) >= len(MOTION_DXL):
            print(f"[OK] Motion sequence completed for {num_servos} servos - {len(MOTION_DXL)} frames processed")
            motion_save_data(1)
        buttons_row2.pack_forget()
        file_input_row.pack(fill="x", pady=(0, 15))
        buttons_row.pack(fill="x")
        file_label.pack(anchor="w", pady=(0, 5))
        entry_input.pack(fill="x", pady=(0, 15))
        tombol_nongroup.pack(side="left", padx=(0, 10))
        tombol_group.pack(side="left")
        tombol_analisis.pack(side="left", padx=(0,10))
        is_pause = False
        is_gerak = False
        is_stop = False
        step = 0
        data_frame = []
        data_hasil = []
        consecutive_failures = 0
        time.sleep(1.5)

def motion_run_nongroupsync():
    global DXL_IDS, DXL_DEGREE, DXL_DEGREE_XL320, DXL_DEGREE_XM430
    global data_hasil, is_pause, is_stop, step, is_gerak, data_frame, data_hasil, consecutive_failures
    print("mulai nongroup")
    # Process each movement frame from the motion data
    for frame_index in range(len(MOTION_DXL)):
        if is_stop or is_pause:
            if is_pause:
                step = frame_index
            break

        if frame_index < step:
            continue

        is_gerak = True

        move_label.configure(text=f'Gerakan {frame_index + 1}/{len(MOTION_DXL)}')

        # Health check before processing frame
        if not servo_health_check():
            if not servo_recover_communication():
                print("[ERROR] Critical failure - stopping test")
                break

        # Extract servo data for current frame
        DXL_IDS = Aerora.getIndexByNotElement(MOTION_DXL[frame_index], "-1")
        DXL_DEGREE = Aerora.getNotValue(MOTION_DXL[frame_index], "-1")
        DXL_DEGREE_XL320, DXL_DEGREE_XM430 = Aerora.getNotValue_v2(MOTION_DXL[frame_index], "-1")

        print(f"[FRAME] Active servos: {DXL_IDS}")
        print(f"[FRAME] Target positions: {DXL_DEGREE}")

        # Create data structure for current frame
        data_frame = motion_create_data_structure(frame_index + 1, 0)

        # Get system resources info
        process = psutil.Process()
        data_frame['cpu_usage_start'] = process.cpu_percent()
        data_frame['memory_usage'] = process.memory_info().rss / 1024 / 1024

        # Execute movement for current frame
        operation_start = time.perf_counter()

        # Write positions to servos
        write_time, write_success = motion_write_nongroupsync_robust(frame_index)

        if not write_success:
            data_frame['error_count'] += 1
            consecutive_failures += 1
            if consecutive_failures >= 5:
                if servo_recover_communication():
                    data_frame['recovery_count'] += 1
                    consecutive_failures = 0
                    write_time, write_success = motion_write_nongroupsync_robust(frame_index)
            if not write_success:
                print("    [ERROR] Write gagal setelah recovery")
                continue

        data_frame['waktu_write'] = write_time
        print(f"    [WRITE] waktu: {write_time:.2f} ms")

        # Wait for servo movement
        time.sleep(0.15)

        # Monitor servo movement until target reached
        cycle_count = 0
        final_positions = None
        consecutive_read_failures = 0
        recovery = 0
        timeout = 0
        success_read = 0
        while True:
            positions, read_time, read_success = motion_read_nongroupsync_robust()
            if not read_success:
                consecutive_read_failures += 1
                data_frame['error_count'] += 1
                consecutive_failures += 1

                if recovery >= 10:
                    final_positions = None
                    break

                if consecutive_read_failures >= 5:
                    print("    [WARNING] Multiple consecutive read failures")
                    if servo_recover_communication():
                        data_frame['recovery_count'] += 1
                        cycle_count += 1
                        consecutive_read_failures = 0
                        recovery += 1
                        continue
                    else:
                        print("    [ERROR] Recovery failed - aborting cycle")
                        break
                time.sleep(0.03)
                cycle_count += 1
                continue

            success_read += 1
            cycle_count += 1
            consecutive_read_failures = 0
            consecutive_failures = 0
            data_frame['waktu_read'] = read_time

            # Check if servos reached target positions
            servos_at_target = 0
            position_errors = []

            for i, servo_id in enumerate(DXL_IDS):
                servo_index = DXL_ALL.index(servo_id)
                present_pos = positions[servo_index]
                goal_pos = DXL_DEGREE[i]
                error = abs(goal_pos - present_pos)
                position_errors.append(error)
                if error <= DXL_MOVING_STATUS_THRESHOLD:
                    servos_at_target += 1

            if cycle_count % 20 == 0 and cycle_count > 0:
                print(f"    [PROGRESS] Cycle {cycle_count}: {servos_at_target}/{len(DXL_IDS)} servos at target")
                print(f"    [ERRORS] Current position errors: {position_errors}")

            if servos_at_target == len(DXL_IDS):
                final_positions = positions[:]
                print(f"    [TARGET] tercapai pada cycle {cycle_count}")
                is_gerak = False
                break

            if servo_check_timeout():
                is_gerak = False
                final_positions = positions[:]
                timeout += 1
                print(f"    [TIMEOUT] Position tidak tercapai dan servo tidak bergerak: {position_errors}")
                print("     [INFO] Gerakan dilanjutkan")
                break

            time.sleep(0.025)

        # Record results for current frame
        if final_positions is not None:
            for i, servo_id in enumerate(DXL_IDS):
                servo_index = DXL_ALL.index(servo_id)
                present_pos = final_positions[servo_index]
                goal_pos = DXL_DEGREE[i]
                error_pos = abs(goal_pos - present_pos)

                servo_key_error = f'error_akhir_servo_{servo_index}'
                servo_key_status = f'status_servo_{servo_index}'
                data_frame[servo_key_error].append(error_pos)
                data_frame[servo_key_status].append(error_pos <= DXL_MOVING_STATUS_THRESHOLD)

            operation_time = (time.perf_counter() - operation_start) * 1000
            data_frame['waktu_operasi'] = operation_time
            print(f"    [OPERATION] waktu total: {operation_time:.2f} ms")
        else:
            print("    [TIMEOUT] Read tidak berhasil membaca")
            timeout += 1
            if 'positions' in locals():
                print(f"    [DEBUG] Last known positions: {positions}")
            print(f"    [DEBUG] Target positions: {DXL_DEGREE}")

        # Update system resource usage
        data_frame['cpu_usage_end'] = process.cpu_percent()
        data_frame['success_read'] = success_read
        data_frame['read_try'] = cycle_count
        data_frame['timeout'] = timeout
        data_hasil.append(data_frame)

        # Print frame results
        print(f"[RESULT] Recoveries: {data_frame['recovery_count']}, Errors: {data_frame['error_count']}")
        print(f"[RESULT] Write Time: {data_frame['waktu_write']} ms")
        print(f"[RESULT] Read Time: {data_frame['waktu_read']}  ms")

        # Wait before next frame (if not last frame)
        if frame_index < len(MOTION_DXL) - 1:
            print("[INFO] Waiting before next frame...")
            time.sleep(0.1)

    if (frame_index+1) >= len(MOTION_DXL) or is_stop:
        if (frame_index+1) >= len(MOTION_DXL):
            print(f"[OK] Motion sequence completed for {num_servos} servos - {len(MOTION_DXL)} frames processed")
            motion_save_data(0)
        buttons_row2.pack_forget()
        file_input_row.pack(fill="x", pady=(0, 15))
        buttons_row.pack(fill="x")
        file_label.pack(anchor="w", pady=(0, 5))
        entry_input.pack(fill="x", pady=(0, 15))
        tombol_nongroup.pack(side="left", padx=(0, 10))
        tombol_group.pack(side="left")
        tombol_analisis.pack(side="left", padx=(0,10))
        is_pause = False
        is_gerak = False
        is_stop = False
        step = 0
        data_frame = []
        data_hasil = []
        consecutive_failures = 0
        time.sleep(1.5)

def motion_save_data(method):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if method == 0:
        metode = "nongroup"
    elif method == 1:
        metode = "groupsync"
    else:
        metode = "groupsync"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    csv_file = os.path.join(save_path, f'{metode}_{input_text}_{num_servos}servo_{timestamp}.csv')

    header = ['Metode', 'Iterasi', 'Servo_IDs', 'Waktu_Write_ms', 'Waktu_Read_ms', 'Waktu_Operasi_ms']

    for i in range(num_servos):
        header.append(f'Error_Akhir_Servo_{i}')

    header.extend([
        'Jumlah_Error', 'Recovery_Count', 'Persentease_Read%', 'Timeout', 'CPU_Usage_Start_%', 'CPU_Usage_End_%', 'Memory_Usage_MB'
    ])

    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for data in data_hasil:
            rata_wr = data['waktu_write']
            rata_rd = data['waktu_read']
            rata_op = data['waktu_operasi']

            rata_errors = []
            sukses_rates = (float(data['success_read']) / float(data['read_try'])) * 100
            for i in range(num_servos):
                error_key = f'error_akhir_servo_{i}'
                rata_error = statistics.mean(data[error_key]) if data[error_key] else 0
                rata_errors.append(rata_error)

            row = [
                data['metode'],
                data['iterasi'],
                str(data['servo_ids']),
                rata_wr, rata_rd, rata_op
            ]
            row.extend(rata_errors)
            row.extend([
                data['error_count'],
                data['recovery_count'],
                round(sukses_rates, 2),
                data['timeout'],
                data['cpu_usage_start'],
                data['cpu_usage_end'],
                data['memory_usage']
            ])

            writer.writerow(row)

    print(f"[SAVE] Data akhir tersimpan di: {csv_file}")

###################
#       GUI       #
###################

###################
#     FUNCTION    #
###################
def gui_on_connect_click():
    global DEVICENAME, connection_status
    current_text = btn_connect.cget("text")
    DEVICENAME = entry_port.get()

    if DEVICENAME == "":
        messagebox.showerror("Gagal Connection", "Catatan: Port kosong")
        return

    if current_text == "Connect":
        # Trying to connect
        btn_connect.configure(state="disabled", text="Connecting...")
        status_label.configure(text="Status: Connecting...", text_color="orange")
        app.update()  # Update UI

        try:
            success, message = servo_connect()

            if success:
                btn_connect.configure(text="Disconnect", fg_color="red", hover_color="darkred")
                status_label.configure(text="Status: Connected", text_color="green")
                connection_status = True
            else:
                btn_connect.configure(text="Connect")
                status_label.configure(text="Status: Disconnected", text_color="red")
                messagebox.showerror("Connection Gagal ", message)
        except Exception as e:
            # Extra safety catch
            btn_connect.configure(text="Connect")
            status_label.configure(text="Status: Disconnected", text_color="red")
            message_label.configure(text=f"Error: {str(e)}", text_color="red")
            connection_status = False

        btn_connect.configure(state="normal")

    else:
        try:
            print("disconnect")
            servo_disconnect()
            btn_connect.configure(text="Connect", fg_color=("gray10", "gray20"), hover_color=("gray20", "gray30"))
            status_label.configure(text="Status: Disconnected", text_color="red")
            connection_status = False

        except Exception as e:
            btn_connect.configure(text="Connect", fg_color=("gray10", "gray20"), hover_color=("gray20", "gray30"))
            status_label.configure(text="Status: Disconnected", text_color="red")
            message_label.configure(text=f"Disconnected with error: {str(e)}", text_color="gray")
            connection_status = False

def gui_update_ports_list():
    ports = Aerora.list_available_ports()
    if ports:
        message_label.configure(text=f"Available ports:\n" + "\n".join(ports), text_color="blue")
    else:
        message_label.configure(text="No ports found", text_color="orange")

def gui_on_groupsync_click():
    global MOTION_TIME_XM430, MOTION_TIME_XL320, MOTION_HEAD, MOTION_HAND, MOTION_FEET, MOTION_DXL, MOTION_DXL_XL320, MOTION_DXL_XM430
    global path, input_text
    if not connection_status:
        messagebox.showwarning("Warning", "Servo belum terkoneksi! Silakan koneksi terlebih dahulu.")
        return

    input_text = entry_input.get()
    if not input_text:
        messagebox.showwarning("Warning", "Masukkan nama file CSV terlebih dahulu!")
        return

    message_test.configure(text='Memuat file....')

    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion")
    filename = f"{entry_input.get()}.csv"
    path = os.path.join(folder, filename)

    stat_success, message = Aerora.cek_file(path)
    if not stat_success:
        messagebox.showerror("Gagal Memuat File", message)

    MOTION_TIME_XM430, MOTION_TIME_XL320, MOTION_HEAD, MOTION_HAND, MOTION_FEET, MOTION_DXL, MOTION_DXL_XL320, MOTION_DXL_XM430 = Aerora.bacaFile_v3(path)
    message_test.configure(text='Berhasil memuat file')

    print(f"=== {num_servos} SERVO SINKRONISASI ===")
    move_label.configure(text=f'Gerakan 0/{len(MOTION_DXL)}')

    message_test.configure(text='Inisialiasi groupsync')
    if not servo_init_groupsync():
        print("[INFOR] Gagal inisialisasi groupsync")
        message_test.configure(text='Gagal inisialisasi groupsync')
        return

    message_test.configure(text='Melakukan posisi siap')
    if not servo_setup_ready_position():
        print("[INFOR] Gagal setup posisi")
        message_test.configure(text='Gagal setup posisi')
        return
    
    buttons_row.pack_forget()
    file_input_row.pack_forget()
    tombol_analisis.pack_forget()

    buttons_row2.pack(fill="x")

    move_label.pack(pady=(0, 5))
    tombol_pause_group.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)

    thread_group = threading.Thread(target=motion_run_groupsync)
    thread_group.start()

def gui_on_nongroupsync_click():
    global MOTION_TIME_XM430, MOTION_TIME_XL320, MOTION_HEAD, MOTION_HAND, MOTION_FEET, MOTION_DXL, MOTION_DXL_XL320, MOTION_DXL_XM430
    global path

    if not connection_status:
        messagebox.showwarning("Warning", "Servo belum terkoneksi! Silakan koneksi terlebih dahulu.")
        return

    input_text = entry_input.get()
    if not input_text:
        messagebox.showwarning("Warning", "Masukkan nama file CSV terlebih dahulu!")
        return

    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion")
    filename = f"{entry_input.get()}.csv"
    path = os.path.join(folder, filename)

    stat_success, message = Aerora.cek_file(path)
    if not stat_success:
        messagebox.showerror("Gagal Memuat File", message)

    MOTION_TIME_XM430, MOTION_TIME_XL320, MOTION_HEAD, MOTION_HAND, MOTION_FEET, MOTION_DXL, MOTION_DXL_XL320, MOTION_DXL_XM430 = Aerora.bacaFile_v3(path)
    message_test.configure(text='Berhasil memuat file')

    print(f"=== {num_servos} SERVO SINKRONISASI ===")
    move_label.configure(text=f'Gerakan 0/{len(MOTION_DXL)}')

    message_test.configure(text='Inisialiasi groupsync')
    if not servo_init_groupsync():
        message_test.configure(text='Gagal Inisialisasi')
        return
    message_test.configure(text='Berhasil')

    time.sleep(0.2)

    message_test.configure(text='Melakukan posisi siap')
    if not servo_setup_ready_position():
        message_test.configure(text='Gagal setup posisi')
        return
    message_test.configure(text='Berhasil')

    message_test.configure(text='Memuat file....')
    
    buttons_row.pack_forget()
    file_input_row.pack_forget()
    tombol_analisis.pack_forget()

    buttons_row2.pack(fill="x")

    move_label.pack(pady=(0, 5))
    tombol_pause_nongroup.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)

    thread_nongroup = threading.Thread(target=motion_run_nongroupsync)
    thread_nongroup.start()

def gui_on_pause_group_click():
    global is_pause
    is_pause = True
    tombol_pause_group.pack_forget()
    tombol_stop.pack_forget()
    time.sleep(0.1)
    tombol_continue_group.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)

def gui_on_pause_nongroup_click():
    global is_pause
    is_pause = True
    tombol_pause_nongroup.pack_forget()
    tombol_stop.pack_forget()
    time.sleep(0.1)
    tombol_continue_nongroup.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)

def gui_on_continue_group_click():
    global is_pause
    if is_gerak:
        messagebox.showwarning("Warning", "Robot masih bergerak.")
        return
    is_pause = False
    tombol_continue_group.pack_forget()
    tombol_stop.pack_forget()
    time.sleep(0.1)
    tombol_pause_group.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)
    time.sleep(0.1)

    thread_group = threading.Thread(target=motion_run_groupsync)
    thread_group.start()

def gui_on_continue_nongroup_click():
    global is_pause
    if is_gerak:
        messagebox.showwarning("Warning", "Robot masih bergerak.")
        return
    is_pause = False
    tombol_continue_nongroup.pack_forget()
    tombol_stop.pack_forget()
    time.sleep(0.1)
    tombol_pause_nongroup.pack(side='left', padx=(205,0))
    tombol_stop.pack(side='left', padx=10)
    time.sleep(0.1)

    thread_nongroup = threading.Thread(target=motion_run_nongroupsync)
    thread_nongroup.start()

def gui_on_stop_click():
    global is_stop, step
    is_stop = True
    step = 0

def gui_on_closing():
    if connection_status:
        portHandler.openPort()
        servo_torque_disable()
        if portHandler:
            portHandler.closePort()
        print("Port ditutup saat aplikasi ditutup")
    app.destroy()

def gui_on_analisis_click():
    input_text = entry_input.get()
    if not input_text:
        messagebox.showwarning("Warning", "Masukkan nama file CSV terlebih dahulu!")
        return
    
    status, message = Aerora.analisis_global(entry_input.get())
    if not status:
        messagebox.showwarning("Warning", message)
        return
    
    jendela_baru = ctk.CTkToplevel(app)
    jendela_baru.title("Hasil Analisis")
    jendela_baru.geometry("600x490")

    message_hasil_group = ctk.CTkLabel(jendela_baru, text="",
                            text_color="gray", wraplength=500, justify="left",
                            font=ctk.CTkFont(size=13))
    message_hasil_group.place(relx=0.1, rely=0.1)

    message_hasil_nongroup = ctk.CTkLabel(jendela_baru, text="",
                                text_color="gray", wraplength=500, justify="left",
                                font=ctk.CTkFont(size=13))
    message_hasil_nongroup.place(relx=0.55, rely=0.1)
    
    message_hasil_intepretasi = ctk.CTkLabel(jendela_baru, text="",
                                text_color="gray", wraplength=500, justify="left",
                                font=ctk.CTkFont(size=13))
    message_hasil_intepretasi.place(relx=0.1, rely=0.58)
    
    message_hasil_group.configure(text=message[0])
    message_hasil_nongroup.configure(text=message[1])
    message_hasil_intepretasi.configure(text=message[2])

def gui_on_kembali_click():
    print("anjay")

#######################
#     INISIALISASI    #
#######################
# Inisialisasi aplikasi
app = ctk.CTk()
app.geometry("600x700")
app.title("AERORA - Servo Control System")
app.resizable(False, False)

# Set protocol untuk menutup aplikasi dengan benar
app.protocol("WM_DELETE_WINDOW", gui_on_closing)

# Main container dengan padding
main_container = ctk.CTkFrame(app, fg_color="transparent")
main_container.pack(fill="both", expand=True, padx=20, pady=20)

# Header
header_label = ctk.CTkLabel(main_container, text="AERORA",
                           font=ctk.CTkFont(size=24, weight="bold"))
header_label.pack(pady=(0, 20))

# Frame untuk connection section
connection_frame = ctk.CTkFrame(main_container)
connection_frame.pack(fill="x", pady=(0, 20))

# Connection section header
connection_title = ctk.CTkLabel(connection_frame, text="Servo Connection",
                               font=ctk.CTkFont(size=16, weight="bold"))
connection_title.pack(pady=(15, 10))

# Connection controls container
connection_controls = ctk.CTkFrame(connection_frame, fg_color="transparent")
connection_controls.pack(fill="x", padx=20, pady=(0, 10))

# Port input row
port_row = ctk.CTkFrame(connection_controls, fg_color="transparent")
port_row.pack(fill="x", pady=(0, 10))

port_label = ctk.CTkLabel(port_row, text="Port:", font=ctk.CTkFont(size=12))
port_label.pack(side="left", padx=(0, 10))

entry_port = ctk.CTkEntry(port_row, width=120, placeholder_text="e.g., COM6")
entry_port.pack(side="left", padx=(0, 10))

btn_connect = ctk.CTkButton(port_row, text="Connect", command=gui_on_connect_click,
                           width=100, height=32)
btn_connect.pack(side="left", padx=(0, 10))

tombol_refresh = ctk.CTkButton(port_row, text="Check Ports", command=gui_update_ports_list,
                              width=100, height=32)
tombol_refresh.pack(side="left")

# Status row
status_row = ctk.CTkFrame(connection_controls, fg_color="transparent")
status_row.pack(fill="x", pady=(0, 10))

status_label = ctk.CTkLabel(status_row, text="Status: Disconnected",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color="red")
status_label.pack(side="left")

# Message area
message_label = ctk.CTkLabel(connection_frame, text="Click 'Check Ports' to see available ports",
                            text_color="gray", wraplength=500, justify="left",
                            font=ctk.CTkFont(size=11))
message_label.pack(pady=(0, 15), padx=20)

# Separator
separator = ctk.CTkFrame(main_container, height=2, fg_color="gray")
separator.pack(fill="x", pady=10)

# Frame untuk file input section
file_frame = ctk.CTkFrame(main_container)
file_frame.pack(fill="x", pady=(0, 20))

# File section header
file_title = ctk.CTkLabel(file_frame, text="Motion Control",
                         font=ctk.CTkFont(size=16, weight="bold"))
file_title.pack(pady=(15, 10))

# File input container
file_container = ctk.CTkFrame(file_frame, fg_color="transparent")
file_container.pack(fill="x", padx=20, pady=(0, 15))

# File input row
file_input_row = ctk.CTkFrame(file_container, fg_color="transparent")
file_input_row.pack(fill="x", pady=(0, 15))

file_label = ctk.CTkLabel(file_input_row, text="", font=ctk.CTkFont(size=12))
file_label.pack(anchor="w", pady=(0, 5))

entry_input = ctk.CTkEntry(file_input_row, placeholder_text="Enter CSV filename (e.g., motion)")
entry_input.pack(fill="x", pady=(0, 15))

# Control buttons row
buttons_row = ctk.CTkFrame(file_container, fg_color="transparent")
buttons_row.pack(fill="x")

buttons_row2 = ctk.CTkFrame(file_container, fg_color="transparent")

tombol_nongroup = ctk.CTkButton(buttons_row, text="NonGroup", command=gui_on_nongroupsync_click,
                               width=150, height=40)
tombol_nongroup.pack(side="left", padx=(0, 10))

tombol_group = ctk.CTkButton(buttons_row, text="GroupSync", command=gui_on_groupsync_click,
                               width=150, height=40)
tombol_group.pack(side="left")

tombol_analisis = ctk.CTkButton(buttons_row, text="Analisis", command=gui_on_analisis_click,
                               width=150, height=40)
tombol_analisis.pack(side="left", padx=(10,0))

tombol_pause_group = ctk.CTkButton(buttons_row2, text="⏸", command=gui_on_pause_group_click,
                               width=50, height=40)

tombol_pause_nongroup = ctk.CTkButton(buttons_row2, text="⏸", command=gui_on_pause_nongroup_click,
                               width=50, height=40)

tombol_continue_group = ctk.CTkButton(buttons_row2, text="▶", command=gui_on_continue_group_click,
                               width=50, height=40)

tombol_continue_nongroup = ctk.CTkButton(buttons_row2, text="▶", command=gui_on_continue_nongroup_click,
                               width=50, height=40)

tombol_stop = ctk.CTkButton(buttons_row2, text="⏹", command=gui_on_stop_click,
                               width=50, height=40)

tombol_back = ctk.CTkButton(buttons_row2, text="Kembali", command=gui_on_kembali_click,
                               width=50, height=40)

move_label = ctk.CTkLabel(buttons_row2, text="Gerakan 0/0", font=ctk.CTkFont(size=12))

message_test = ctk.CTkLabel(file_frame, text="",
                            text_color="gray", wraplength=500, justify="left",
                            font=ctk.CTkFont(size=11))
message_test.pack(pady=(0, 15), padx=20)


# Footer dengan informasi
footer_frame = ctk.CTkFrame(main_container, fg_color="transparent")
footer_frame.pack(fill="x", side="bottom")

info_title = ctk.CTkLabel(footer_frame, text="Information:",
                         font=ctk.CTkFont(size=12, weight="bold"))
info_title.pack(anchor="w", pady=(0, 5))

info_text = """• Ensure servo is connected before running motion
• CSV file must be in the same directory as this program
• Use 'Check Ports' to see available serial ports
• Connect to servo before executing any motion commands"""

info_label = ctk.CTkLabel(footer_frame, text=info_text,
                         text_color="gray", wraplength=550, justify="left",
                         font=ctk.CTkFont(size=11))
info_label.pack(anchor="w")

btn_connect.configure(fg_color=("gray10", "gray20"), hover_color=("gray20", "gray30"))

if __name__ == "__main__":
    app.mainloop()