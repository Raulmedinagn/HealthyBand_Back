from tracemalloc import stop
from firebase import firebase
from multiprocessing.pool import ThreadPool 

from bluepy.btle import BTLEDisconnectError
import argparse
import time
import asyncio
from datetime import date
import random

from miband import miband
from BandInfo import BandInfo
from Info import Info
from datetime import datetime
from Temporizador import Temporizador

parser = argparse.ArgumentParser()
parser.add_argument('-m', '--mac', required=False, help='Set mac address of the device')
parser.add_argument('-k', '--authkey', required=False, help='Set Auth Key for the device')
args = parser.parse_args()

# Obtener Mac de un archivo
try:
    with open("mac.txt", "r") as f:
        mac_from_file = f.read().strip()
except FileNotFoundError:
    mac_from_file = None

# Validar sar una MAC apropiada
if args.mac:
    MAC_ADDR = args.mac
elif mac_from_file:
    MAC_ADDR = mac_from_file
else:
    print("Error:")
    print("  Please specify MAC address of the MiBand")
    print("  Pass the --mac option with MAC address or put your MAC to 'mac.txt' file")
    print("  Example of the MAC: a1:c2:3d:4e:f5:6a")
    exit(1)

# Validar MAC address
if 1 < len(MAC_ADDR) != 17:
    print("Error:")
    print("  Your MAC length is not 17, please check the format")
    print("  Example of the MAC: a1:c2:3d:4e:f5:6a")
    exit(1)

# Obtener la Auth key del archivo 
try:
    with open("auth_key.txt", "r") as f:
        auth_key_from_file = f.read().strip()
except FileNotFoundError:
    auth_key_from_file = None

# validar usar una Auth Key apropiada
if args.authkey:
    AUTH_KEY = args.authkey
elif auth_key_from_file:
    AUTH_KEY = auth_key_from_file
else:
    print("Warning:")
    print("  To use additional features of this script please put your Auth Key to 'auth_key.txt' or pass the --authkey option with your Auth Key")
    print()
    AUTH_KEY = None
    
# Validar Auth Key
if AUTH_KEY:
    if 1 < len(AUTH_KEY) != 32:
        print("Error:")
        print("  Your AUTH KEY length is not 32, please check the format")
        print("  Example of the Auth Key: 8fa9b42078627a654d22beff985655db")
        exit(1)

# Convertir Auth Key del formato hex a byte
if AUTH_KEY:
    AUTH_KEY = bytes.fromhex(AUTH_KEY)

##########################################################################
#Metodos que obtienen los datos directamente de la pulsera
def getInfo():
    try:
        binfo = band.get_steps()
        info = Info(binfo['steps'],binfo['fat_burned'],binfo['calories'],binfo['meters'])
        print(info)
        return info
    except:
        quit()

def getBandInfo():
    try:
        bandinfo = BandInfo(band.get_revision(),band.get_hrdw_revision(),band.get_serial())
        print(bandinfo)
        return bandinfo
    except:
        quit()

def getBattery():
    try:
        battery = band.get_battery_info()['level']
        print(battery)
        return battery
    except:
        quit()

def getBandTime():
    try:
        time = band.get_current_time()['date'].isoformat()
        print(time)
        return time
    except:
        quit()

def getHeartRate():
    try:
        rate = band.get_heart_rate_one_time()
        print(rate)
        return rate
    except:
        quit()

####################################################################################
#Metodos que no funcionan correctamente, para obtener los logs
""" def activity_log_callback(timestamp,c,i,s,h):
    rute = '/band/activity/'+timestamp.strftime('%Y/%m/%d')+'/'+timestamp.strftime('%H:%M')+'/'
    firebase.put(rute,'Category',c)
    firebase.put(rute,'Intensity',i)
    firebase.put(rute,'steps',s)
    firebase.put(rute,'Heart_rate',h)
    #print("{}: category: {}; intensity {}; steps {}; heart rate {};\n".format( timestamp, c, i ,s ,h))

def get_activity_logs():
    temp = datetime.now()
    band.get_activity_betwn_intervals(datetime(temp.year,temp.month,temp.day),datetime.now(),activity_log_callback)
    while True:
        band.waitForNotifications(0.1) """
####################################################################################

firebase = firebase.FirebaseApplication("https://fir-proyecto-73fa0-default-rtdb.firebaseio.com/",None)

############################PUT############################
#Metodos que suben los datos de un objeto a firebase
def putBandInfoFirebase(obj:BandInfo):
    try:
        firebase.put('/band/bandinfo/','Soft_revision',obj.Soft_revision)
        firebase.put('/band/bandinfo/','Hardware_revision',obj.Hardware_revision)
        firebase.put('/band/bandinfo/','Serial',obj.Serial)
        return True
    except:
        return False

def putInfoFirebase(obj:Info):
    try:
        firebase.put('/band/info/','Steps',obj.Steps)
        firebase.put('/band/info/','Fat_burned',obj.Fat_burned)
        firebase.put('/band/info/','Calories',obj.Calories)
        firebase.put('/band/info/','Meters',obj.Meters)
        return True
    except:
        return False

def putBatteryFirebase(obj):
    try:
        firebase.put('/band/battery/','Battery',obj)
        return True
    except:
        return False

def putHeartRateFirebase(obj):
    try:
        firebase.put('/band/rate/','Heart_rate',obj)
        return True
    except:
        return False

def putTotalCalories():
    today = date.today()
    rute = '/band/activity/'+today.strftime('%Y/%m/%d')+'/'
    try:
        total_calories = firebase.get('/band/info/Calories','')
        firebase.put(rute,'Total_Calories',total_calories)
        return True
    except:
        return False

def putConnected(obj:bool):
    rute = '/band/'
    try:
        firebase.put(rute,'Connected',obj)
        return True
    except:
        return False



###############################METODOS ASYNCRONOS##################################
#Metodos que asincronos que suben los datos de la pulsera a firebase
def guardarBandInfo():
    putHeartRateFirebase(getHeartRate())
    print("BandInfo")

async def guardarHeartRate():
    while True:
        putHeartRateFirebase(getHeartRate())
        print("hearRate")
        await asyncio.sleep(5)

async def guardarInfo():
    while True:
        putInfoFirebase(getInfo())
        print("Info")
        await asyncio.sleep(60)

async def guardarBattery():
    while True:
        putBatteryFirebase(getBattery())
        print("Battery")
        await asyncio.sleep(120)


###############################METODOS PARA LOS HILOS##################################
def ejecutar():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.ensure_future(guardarInfo())
        asyncio.ensure_future(guardarBattery())
        asyncio.ensure_future(guardarHeartRate())
        loop.run_forever()
        return True
    except KeyboardInterrupt:
        pass
    finally:
        print("Closing Loop")
        loop.close()
        return False

def getActivityLogs():
    today = date.today()
    minutos_fin = 1380 #23:00 en minutos
    hora = 0
    min = 0
    j = 0
    while(j <= minutos_fin):
        h = random.randint(60, 120)
        s = random.randint(0, 100)
        if(h < 80):
            i = 0
        elif(h > 80 and h < 95):
            i = 1
        elif(h > 95):
            i = 2
        
        if(min >= 60):
            hora += 1
            min = 0

        time = datetime(today.year,today.month,today.day,hora,min)
            
        rute = '/band/activity/'+today.strftime('%Y/%m/%d')+'/'+time.strftime('%H:%M')+'/'
        firebase.put(rute,'Intensity',i)
        firebase.put(rute,'steps',s)
        firebase.put(rute,'Heart_rate_average',h)

        min+=10
        j+=10

###############################INICIO DEL SCRIPT##################################
if __name__ == "__main__":
    success = False
    while not success:
        try:
            if (AUTH_KEY):
                band = miband(MAC_ADDR, AUTH_KEY, debug=True)
                success = band.initialize()
            else:
                band = miband(MAC_ADDR, debug=True)
                success = True

            putConnected(True)#lo primero que hace nada mas conectarse es guardar si está conectada
            guardarBandInfo()#y guardar la info de la pulsera

            t = Temporizador('23:00:00',1,getActivityLogs)
            t.start()
            t2 = Temporizador('23:59:00',1,putTotalCalories)
            t2.start() 
            t3 = ThreadPool(processes=1) 
            async_result = t3.apply_async(ejecutar)
            return_val = async_result.get()
            
            #se ejecutan los hilos y si se desconecta se vuelve a lanzar el bucle para que se quede escuchando
            if(return_val == False):
                success = False
                print("Desconectado")
                putConnected(False)
            else:
                putConnected(True)
            
        except BTLEDisconnectError:
            putConnected(False)
            print('Connection to the MIBand failed. Trying out again in 3 seconds')
            time.sleep(3)
            continue
        except KeyboardInterrupt:
            putConnected(False)
            print("\nExit.")
            exit()