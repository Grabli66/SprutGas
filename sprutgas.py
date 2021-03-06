import core
import MOD

# работа с ведущим газоанализатором
MASTER_GAS_MODE = "0"
# работа с БУПС
BUPS_MODE = "1"
# приём SMS и передача на пульт
SMS_RECIEVE_MODE = "2"

# Режим отправки на телефонные номера
SEND_MODE_PHONE = "0"
# Режим отправки на модем системы дубль
SEND_MODE_MODEM = "1"

# Ключи в настройках
# Скорость на серийном порту
SER_SP = "SER_SP"
# Скорость на серийном порту для отладки
DEBUG_SER_SP = "DEBUG_SER_SP"
# Режим работы последовательного порта для отладки
DEBUG_SER_OD = "DEBUG_SER_OD"
# Тип байта на серийном порту
SER_OD = "SER_OD"
# Выводить отладку
DEBUG_SER = "DEBUG_SER"
# Режим отправки SMS
SEND_MODE = "SEND_MODE"
# Режим работы
WORK_MODE = "WORK_MODE"

# Период проверки СМС
SMS_READ_PERIOD = "SMS_READ_PERIOD"
# Период срабатывания охранного таймера
WATCHDOG_PERIOD = "WATCHDOG_PERIOD"
# Таймаут отсутствия связи
CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"

# Максимальный адрес устройства
MAX_ADDRESS = 255
# Таймаут чтения
READ_TIMEOUT = 1
# Таймаут чтения БУПС
READ_BUPS_TIMEOUT = 10
# Таймаут чтения ведущего газоанализатора
READ_MASTER_GAS_TIMEOUT = 10
# Количество байт в пакете от БУПС
BUPS_PACK_SIZE = 8

# Таймаут ожидания запуска после рестарта
REBOOT_WAIT_TIMEOUT = 100

# Задержка в работе
WORK_DELAY = 1

# Адресс БУПС
BUPS_NETWORK = 0xE1

# Адрес ведущего газоанализатора
MASTER_GAS_NETWORK = 0xE1

# Текст сообщений
NO_CONNECTION_TEXT = "Нет связи с системой СГК"
CONNECTED_TEXT = "Связь с системой СГК установлена"
NO_DEVICES = "Не заданы устройства"

# Коды тревог
CLAPAN_OPENED = 8
CLAPAN_CLOSED = 9

# Информация об устройстве и его состоянии
class DeviceInfo:
    # Конструктор
    def __init__(self, network):
        self.network = network
        self.connected = core.FALSE
        self.onConnectionTimeout = 0
    
    def __str__(self):
        return str(self.network)

# Состояние БУПС тревог
class BupsAlarmState:
    # Конструктор
    def __init__(self, one, two, three, four):
        self.one = one
        self.two = two
        self.three = three
        self.four = four
    
    # Преобразует в строку
    def __str__(self):
        return str(self.one) + "_" + str(self.two) + "_" + str(self.three) + "_" + str(self.four)

# Описание тревоги
class Alarm:
    # Конструктор
    # code - код тревоги    
    # txt - текстовое описание
    # state - состояние: вкл/откл
    def __init__(self, code, text, state = core.TRUE):
        self.code = code
        self.state = state
        self.text = text

# Для получения списка абонентов кому рассылать
class RecepientHelper:
    # Конструктор
    def __init__(self, config, gsm, debug):
        self.config = config
        self.gsm = gsm
        self.debug = debug

    # Возвращает список кому отправить SMS в зависимости от настроек
    def getRecepients(self):
        # Переключается на СИМ карту
        self.gsm.sendATMdmDefault("AT+CPBS=SM\r", "OK")        
        sendMode = self.config.get(SEND_MODE)

        # Читает 10 номеров из телефона
        a, s = self.gsm.sendATMdmDefault("AT+CPBR=1,10\r", "OK")        
        phoneItems = s.split("+CPBR: ")
        self.debug.send(str(phoneItems))

        phones = []
        for item in phoneItems:
            its = item.split(",")
            if (len(its) > 3):
                val = its[1].strip().replace('"', '')
                if len(val) > 0:
                    phones.append(val)

        if sendMode == SEND_MODE_PHONE:
            return phones
        elif sendMode == SEND_MODE_MODEM:
            if (len(phones) > 0):
                return [phones[0]]
            else:
                return []

# Хранилище тревог
# Если есть изменение тревоги сигнализирует об этом
class AlarmStorage:
    # Конструктор
    def __init__(self):
        self.alarms = {}

    # Добавляет тревогу и возвращает её если она новая
    def add(self, alarms):
        res = []  # Снятые тревоги
        # Ищет снятые тревоги
        for item in self.alarms.items():
            key = item[0]
            storedAlarm = item[1]
            found = core.FALSE
            for inAlarm in alarms:
                if inAlarm.code == storedAlarm.code:
                    found = core.TRUE
                    break
            
            # Сохранённая тревога не найдена == снятие тревоги
            if found == core.FALSE:
                res.append(Alarm(storedAlarm.code, storedAlarm.text, core.FALSE))
        
        # Удаляет снятые тревоги
        for alarm in res:
            del self.alarms[alarm.code]

        # Очищает снятые тревоги в буффере
        res = []

        # Ищет установленные тревоги
        for inAlarm in alarms:
            if not self.alarms.has_key(inAlarm.code):
                alarm = Alarm(inAlarm.code, inAlarm.text)
                self.alarms[inAlarm.code] = alarm
                res.append(alarm)

        return res

# Парсер тревог полученных от устройства
class AlarmParser:
    def __init__(self):
        pass

    # Парсит тревоги газ анализаторов и первый байт бупса
    def parseOne(self, code):
        alarms = []
        if (code & 0x40 > 0) and (code & 0x01 > 0):
            alarms.append(Alarm(1, "Второй порог СО"))
        if (code & 0x40 == 0) and (code & 0x01 > 0):
            alarms.append(Alarm(2, "Второй порог СН4"))
        if (code & 0x04 > 0):
            alarms.append(Alarm(3, "Неисправность"))
        if (code & 0x01 == 0) and (code & 0x02 > 0) and (code & 0x04 == 0) and (code & 0x40 == 0):
            alarms.append(Alarm(4, "Первый порог СН4"))
        if (code & 0x01 == 0) and (code & 0x04 == 0) and (code & 0x08 > 0) and (code & 0x40 == 0):
            alarms.append(Alarm(5, "Первый порог СО"))
        if (code & 0x01 == 0) and (code & 0x04 == 0) and (code & 0x08 > 0) and (code & 0x40 > 1):
            alarms.append(Alarm(6, "Первый порог СН4"))
        if (code & 0x01 == 0) and (code & 0x02 > 0) and (code & 0x04 == 0) and (code & 0x40 > 1):
            alarms.append(Alarm(7, "Первый порог СО"))
        if (code & 0x10 == 0):
            alarms.append(Alarm(CLAPAN_OPENED, "Клапан открыт"))
        else:
            alarms.append(Alarm(CLAPAN_CLOSED, "Клапан закрыт"))
        
        return alarms

    # Парсит тревоги из второго байта бупс
    def parseTwo(self, code):
        alarms = []
        if (code & 0x01 > 0):
            alarms.append(Alarm(20, "Постановка на охрану"))
        if (code & 0x02 > 0):
            alarms.append(Alarm(21, "Взлом"))
        if (code & 0x04 > 0):
            alarms.append(Alarm(22, "Пожар"))
        if (code & 0x08 > 0):
            alarms.append(Alarm(23, "Авария 1"))
        if (code & 0x10 > 0):
            alarms.append(Alarm(24, "Авария 2"))
        
        return alarms

    # Парсит тревоги из третьего байта бупс
    def parseThree(self, code):
        alarms = []
        if (code & 0x01 > 0):
            alarms.append(Alarm(30, "Авария 3"))
        if (code & 0x02 > 0):
            alarms.append(Alarm(31, "Авария 4"))
        if (code & 0x04 > 0):
            alarms.append(Alarm(32, "Авария 5"))
        if (code & 0x08 > 0):
            alarms.append(Alarm(33, "Авария 6"))
        if (code & 0x10 > 0):
            alarms.append(Alarm(34, "Авария 7"))
        
        return alarms


    # Парсит тревоги из четвёртого байта бупс
    def parseFour(self, code):
        alarms = []
        if (code & 0x01 > 0):
            alarms.append(Alarm(40, "Авария 8"))
        if (code & 0x02 > 0):
            alarms.append(Alarm(41, "Авария 9"))
        if (code & 0x04 > 0):
            alarms.append(Alarm(42, "Авария 10"))
        if (code & 0x08 > 0):
            alarms.append(Alarm(43, "Авария 11"))
        if (code & 0x10 > 0):
            alarms.append(Alarm(44, "Авария 12"))
        
        return alarms

    # Преобразует тревоги в массив байт тревог
    def encodeAlarmsToBups(self, alarms):
        one = 0
        two = 0x80
        three = 0xA0
        four = 0xC0
        for alarm in alarms:
            # Второй порог СО
            if alarm == 1:
                one = one | 0x41
            # Второй порог СН4
            if alarm == 2:                
                one = one | 0x01
            # Неисправность
            if alarm == 3:
                one = one | 0x04
            # Первый порог СН4
            if alarm == 4:
                one = one | 0x02
            # Первый порог СО
            if alarm == 5:
                one = one | 0x08
            # Первый порог СН4
            if alarm == 6:
                one = one | 0x48
            # Первый порог СО
            if alarm == 7:
                one = one | 0x44
            # Клапан закрыт
            if alarm == CLAPAN_CLOSED:
                one = one | 0x10

            if alarm == 20:
                two = two | 0x01
            if alarm == 21:
                two = two | 0x02
            if alarm == 22:
                two = two | 0x04
            if alarm == 23:
                two = two | 0x08
            if alarm == 24:
                two = two | 0x10
            
            if alarm == 40:
                four = four | 0x01
            if alarm == 41:
                four = four | 0x02
            if alarm == 42:
                four = four | 0x04
            if alarm == 43:
                four = four | 0x08
            if alarm == 44:
                four = four | 0x10
            
        return [one, two, three, four]

# Обеспечивает работу в режиме прослушивания ведущего назоанализатора
class MasterGasWorker:
    # Конструктор
    def __init__(self, config):
        self.config = config

        self.speed = config.get(SER_SP)
        self.serial = core.Serial()        

        isDebug = config.get(DEBUG_SER) == "1"
        debugSpeed = config.get(DEBUG_SER_SP)
        debugBytetype = config.get(DEBUG_SER_OD)
        self.debug = core.Debug(isDebug, self.serial,
                                debugSpeed, debugBytetype)
        
        self.gsm = core.Gsm(config, self.serial, self.debug)
        self.gsm.simpleInit()
        
        self.smsManager = core.SmsManager(self.gsm, self.debug)
        self.smsManager.initContext()
        # Удаляет все СМС
        self.smsManager.deleteAll()
        self.smsReadTimer = 0
        self.resetSmsTimer()

        self.alarmParser = AlarmParser()
        self.alarmOne = AlarmStorage()
        self.recepientHelper = RecepientHelper(self.config, self.gsm, self.debug)
        self.globalConnected = None
        
        # Таймаут отсутствия связи в неопределенном состоянии
        self.onConnectionTimeout = MOD.secCounter() + int(self.config.get(CONNECTION_TIMEOUT))
        self.initWatchdog()

    # Сбрасывает таймер чтения СМС
    def resetSmsTimer(self):
        self.debug.send("Reset Sms Timer")
        self.smsReadTimer = MOD.secCounter() + int(self.config.get(SMS_READ_PERIOD))

    # Инициализирует охранный таймер
    def initWatchdog(self):
        MOD.watchdogEnable(int(self.config.get(WATCHDOG_PERIOD)))

    # Сбрасывает охранный таймер
    def resetWatchdog(self):
        MOD.watchdogReset()    

    # Обрабатывает тревоги загоанализатора
    def processStates(self, gasState):
        total = []
        
        alarms = self.alarmParser.parseOne(gasState)
        for alarm in self.alarmOne.add(alarms):
            total.append(alarm)

        return total

    # Отправляет всем
    def sendToRecepients(self, text):
        for recepient in self.recepients:
            self.debug.send("SEND ALARM TO RECEPIENTS")
            self.smsManager.sendSms(recepient, text)
            #self.debug.send(text)

    # Возвращает все тревоги
    def getTotalAlarms(self):
        total = []
        for alarm in self.alarmOne.alarms.values():
            total.append(alarm)
        return total

    # Обрабатывает SMS с командой
    def processSms(self):
        self.debug.send("Process SMS")

        if MOD.secCounter() < self.smsReadTimer:
            self.debug.send("Wait for SMS read")
            return

        allSms = None

        try:
            allSms = self.smsManager.listSms()
        except Exception, e:
            self.debug.send("List SMS error")
            self.debug.send(str(e))
        
        self.smsManager.deleteAll()
        self.resetSmsTimer()

        if allSms == None:
            return

        recepients = []
        for sms in allSms:
            for recep in self.recepients:
                smsRec = sms.recepient.replace("+7", "8")
                storRec = recep.replace("+7", "8")
                self.debug.send("SMS recepient: " + smsRec)
                self.debug.send("Stored recepient: " + storRec)
                if smsRec == storRec:
                    recepients.append(storRec)
        
        self.debug.send("Recepients: " + str(recepients))        
        totalAlarms = self.getTotalAlarms()
        count = len(totalAlarms)
        self.debug.send("Alarm count: " + str(count))
        txt = ""
        # Клапан или открыт или закрыт
        if count == 0:
            txt = "Состояние неизвестно"
        elif count == 1:
            alarm = totalAlarms[0]
            txt = "Аварий нет. " + alarm.text
        else:
            clapanIsOpen = core.FALSE
            for alarm in totalAlarms:
                if alarm.code == CLAPAN_OPENED:
                    clapanIsOpen = core.TRUE
                elif alarm.code == CLAPAN_CLOSED:
                    clapanIsOpen = core.FALSE
                else:
                    txt = txt + alarm.text + ", "
            
            if clapanIsOpen == core.TRUE:
                txt = txt + "Клапан открыт"
            else:
                txt = txt + "Клапан закрыт"

        for rec in recepients:
            self.smsManager.sendSms(rec, txt)        

    # Проверяет есть ли связь. Отсылает SMS если не было связи в течении 3-х минут
    # Или отсылает SMS что связь появилась
    def checkConnection(self, gasState):
        self.debug.send("Check connection")

        connected = core.FALSE
        if gasState != None:
            connected = core.TRUE

        self.debug.send("Connected: " + str(connected))
        self.debug.send("Global Connected: " + str(self.globalConnected))
        
        if connected == core.TRUE:
            self.onConnectionTimeout = MOD.secCounter() + int(self.config.get(CONNECTION_TIMEOUT))

        # Если неопределённое состояние
        if self.globalConnected == None:
            if (connected == core.FALSE) and (MOD.secCounter() > self.onConnectionTimeout):
                self.sendToRecepients(NO_CONNECTION_TEXT)
                self.globalConnected = core.FALSE
            elif connected == core.TRUE:
                self.sendToRecepients(CONNECTED_TEXT)
                self.globalConnected = core.TRUE
        # Если находится в состоянии подключения
        # Отсылает СМС и устанавливает состояние не соединено
        elif self.globalConnected == core.TRUE:
            if (connected == core.FALSE) and (MOD.secCounter() > self.onConnectionTimeout):
                self.sendToRecepients(NO_CONNECTION_TEXT)
                self.globalConnected = core.FALSE
        # Если не подключен
        else:
            if connected == core.TRUE:
                self.sendToRecepients(CONNECTED_TEXT)
                self.globalConnected = core.TRUE

    # Читает четыре байта состояний
    def readGasState(self):
        self.debug.send("Read gas state")
               
        data = []
        state = 0 # состояние: начало пакета(0), тревога(1)

        timeout = MOD.secCounter() + READ_MASTER_GAS_TIMEOUT
        gasState = None
        while (timeout > MOD.secCounter()):
            byte = self.serial.receivebyte(self.speed, '8N1', 0)
            # Ищет начало пакета
            if state == 0:
                if (byte == MASTER_GAS_NETWORK):
                    state = 1
                continue
            
            if state == 1:
                gasState = byte
                break
            else:
                state = 0

        self.debug.send("Gas state: " + str(gasState))

        # Очищает буффер модема, что бы не переполнился
        clean = self.serial.receive(self.speed, '8N1', 0)
        self.debug.send("Bytes to clean: " + str(len(clean)))        

        return gasState

    # Запускает
    def start(self):
        self.recepients = self.recepientHelper.getRecepients()
        self.debug.send(str(self.recepients))
        self.work()
    
    # Основная работа
    def work(self):
        self.debug.send("Start work")
        while(core.TRUE):
            try:
                # Отсылает запрос состояния каждому газоанализатору
                gasState = self.readGasState()
                self.checkConnection(gasState)
                
                # Пока состояние неизвестно не отсылает ничего
                if (gasState != None) and (self.globalConnected != None):
                    alarms = self.processStates(gasState)
                    alarmIds = []
                    for alarm in alarms:
                        txt = str(alarm.code) + " - " + alarm.text
                        alarmIds.append(alarm.code)
                        self.sendToRecepients(txt)
                    self.debug.send("ALARMS: " + str(alarmIds))

                # Получает СМС и отправляет последнее состояние
                self.processSms()
                # Сбрасывает охранный таймер
                self.resetWatchdog()
            except Exception, e:
                self.debug.send("Work error")
                self.debug.send(str(e))

# Обеспечивает работу в режиме прослушивания БУПС
class BupsWorker:
    # Конструктор
    def __init__(self, config):
        self.config = config

        self.speed = config.get(SER_SP)
        self.serial = core.Serial()        

        isDebug = config.get(DEBUG_SER) == "1"
        debugSpeed = config.get(DEBUG_SER_SP)
        debugBytetype = config.get(DEBUG_SER_OD)
        self.debug = core.Debug(isDebug, self.serial,
                                debugSpeed, debugBytetype)
        
        self.gsm = core.Gsm(config, self.serial, self.debug)
        self.gsm.simpleInit()
        
        self.smsManager = core.SmsManager(self.gsm, self.debug)
        self.smsManager.initContext()
        # Удаляет все СМС
        self.smsManager.deleteAll()
        self.smsReadTimer = 0
        self.resetSmsTimer()

        self.alarmParser = AlarmParser()
        self.alarmOne = AlarmStorage()
        self.alarmTwo = AlarmStorage()
        self.alarmThree = AlarmStorage()
        self.alarmFour = AlarmStorage()
        self.recepientHelper = RecepientHelper(self.config, self.gsm, self.debug)
        self.globalConnected = None
        
        # Таймаут отсутствия связи в неопределенном состоянии
        self.onConnectionTimeout = MOD.secCounter() + int(self.config.get(CONNECTION_TIMEOUT))
        self.initWatchdog()

    # Сбрасывает таймер чтения СМС
    def resetSmsTimer(self):
        self.debug.send("Reset Sms Timer")
        self.smsReadTimer = MOD.secCounter() + int(self.config.get(SMS_READ_PERIOD))

    # Инициализирует охранный таймер
    def initWatchdog(self):
        MOD.watchdogEnable(int(self.config.get(WATCHDOG_PERIOD)))

    # Сбрасывает охранный таймер
    def resetWatchdog(self):
        MOD.watchdogReset()    

    # Обрабатывает пакет БУПС
    # idx - номер байта
    # code - код тревоги
    # возвращает список тревог
    def processStates(self, bupsState):
        total = []
        
        alarms = self.alarmParser.parseOne(bupsState.one)
        for alarm in self.alarmOne.add(alarms):
            total.append(alarm)
        
        alarms = self.alarmParser.parseTwo(bupsState.two)
        for alarm in self.alarmTwo.add(alarms):
            total.append(alarm)
        
        alarms = self.alarmParser.parseThree(bupsState.three)
        for alarm in self.alarmThree.add(alarms):
            total.append(alarm)
        
        alarms = self.alarmParser.parseFour(bupsState.four)
        for alarm in self.alarmFour.add(alarms):
            total.append(alarm)

        return total

    # Отправляет всем
    def sendToRecepients(self, text):
        for recepient in self.recepients:
            self.debug.send("SEND ALARM TO RECEPIENTS")
            self.smsManager.sendSms(recepient, text)
            #self.debug.send(text)

    # Возвращает все тревоги
    def getTotalAlarms(self):
        total = []
        for alarm in self.alarmOne.alarms.values():
            total.append(alarm)
        for alarm in self.alarmTwo.alarms.values():
            total.append(alarm)
        for alarm in self.alarmThree.alarms.values():
            total.append(alarm)
        for alarm in self.alarmFour.alarms.values():
            total.append(alarm)
        return total

    # Обрабатывает SMS с командой
    def processSms(self):
        self.debug.send("Process SMS")

        if MOD.secCounter() < self.smsReadTimer:
            self.debug.send("Wait for SMS read")
            return

        allSms = None

        try:
            allSms = self.smsManager.listSms()
        except Exception, e:
            self.debug.send("List SMS error")
            self.debug.send(str(e))
        
        self.smsManager.deleteAll()
        self.resetSmsTimer()

        if allSms == None:
            return

        recepients = []
        for sms in allSms:
            for recep in self.recepients:
                smsRec = sms.recepient.replace("+7", "8")
                storRec = recep.replace("+7", "8")
                self.debug.send("SMS recepient: " + smsRec)
                self.debug.send("Stored recepient: " + storRec)
                if smsRec == storRec:
                    recepients.append(storRec)
        
        self.debug.send("Recepients: " + str(recepients))        
        totalAlarms = self.getTotalAlarms()
        count = len(totalAlarms)
        self.debug.send("Alarm count: " + str(count))
        txt = ""
        # Клапан или открыт или закрыт
        if count == 0:
            txt = "Состояние неизвестно"
        elif count == 1:
            alarm = totalAlarms[0]
            txt = "Аварий нет. " + alarm.text
        else:
            clapanIsOpen = core.FALSE
            for alarm in totalAlarms:
                if alarm.code == CLAPAN_OPENED:
                    clapanIsOpen = core.TRUE
                elif alarm.code == CLAPAN_CLOSED:
                    clapanIsOpen = core.FALSE
                else:
                    txt = txt + alarm.text + ", "
            
            if clapanIsOpen == core.TRUE:
                txt = txt + "Клапан открыт"
            else:
                txt = txt + "Клапан закрыт"

        for rec in recepients:
            self.smsManager.sendSms(rec, txt)        

    # Проверяет есть ли связь. Отсылает SMS если не было связи в течении 3-х минут
    # Или отсылает SMS что связь появилась
    def checkConnection(self, bupsState):
        self.debug.send("Check connection")

        connected = core.FALSE
        if bupsState != None:
            connected = core.TRUE

        self.debug.send("Connected: " + str(connected))
        self.debug.send("Global Connected: " + str(self.globalConnected))
        
        if connected == core.TRUE:
            self.onConnectionTimeout = MOD.secCounter() + int(self.config.get(CONNECTION_TIMEOUT))

        # Если неопределённое состояние
        if self.globalConnected == None:
            if (connected == core.FALSE) and (MOD.secCounter() > self.onConnectionTimeout):
                self.sendToRecepients(NO_CONNECTION_TEXT)
                self.globalConnected = core.FALSE
            elif connected == core.TRUE:
                self.sendToRecepients(CONNECTED_TEXT)
                self.globalConnected = core.TRUE
        # Если находится в состоянии подключения
        # Отсылает СМС и устанавливает состояние не соединено
        elif self.globalConnected == core.TRUE:
            if (connected == core.FALSE) and (MOD.secCounter() > self.onConnectionTimeout):
                self.sendToRecepients(NO_CONNECTION_TEXT)
                self.globalConnected = core.FALSE
        # Если не подключен
        else:
            if connected == core.TRUE:
                self.sendToRecepients(CONNECTED_TEXT)
                self.globalConnected = core.TRUE

    # Читает четыре байта состояний
    def readBupsState(self):
        self.debug.send("Read bups state")
               
        data = []
        state = 0 # состояние: начало пакета(0), адрес бупс(1), тревога(2)

        timeout = MOD.secCounter() + READ_BUPS_TIMEOUT
        bupState = None
        while (timeout > MOD.secCounter()):
            byte = self.serial.receivebyte(self.speed, '8N1', 0)
            # Ищет начало пакета
            if state == 0:
                if (byte == BUPS_NETWORK):
                    state = 1
                continue                    

            # Если 7 бит у байта тревоги снят то это начало
            if state == 1:
                if ((byte & 0x80) > 0) and ((byte & 0x40) == 0) and ((byte & 0x20) == 0):
                    state = 2
                    data.append(byte)
                else:
                    state = 0
                continue

            # Продолжает получать байты пока в списке не будет 4 байта данных
            if state == 2:
                if (byte == BUPS_NETWORK):
                    state = 3                
                continue
            
            if state == 3:
                state = 2
                data.append(byte)
                if len(data) >= 4:
                    bupState = BupsAlarmState(data[3], data[0], data[1], data[2])
                    break

        # Очищает буффер модема, что бы не переполнился
        clean = self.serial.receive(self.speed, '8N1', 0)
        self.debug.send("Bytes to clean: " + str(len(clean)))

        self.debug.send(str(bupState))

        return bupState

    # Запускает
    def start(self):
        self.recepients = self.recepientHelper.getRecepients()
        self.debug.send(str(self.recepients))
        self.work()

    # Основная работа
    def work(self):
        self.debug.send("Start work")
        while(core.TRUE):
            try:
                # Отсылает запрос состояния каждому газоанализатору
                bupsState = self.readBupsState()
                self.checkConnection(bupsState)
                
                # Пока состояние неизвестно не отсылает ничего
                if (bupsState != None) and (self.globalConnected != None):
                    alarms = self.processStates(bupsState)
                    alarmIds = []                    
                    for alarm in alarms:
                        txt = str(alarm.code) + " - " + alarm.text
                        alarmIds.append(alarm.code)
                        self.sendToRecepients(txt)
                    self.debug.send("ALARMS: " + str(alarmIds))

                # Получает СМС и отправляет последнее состояние
                self.processSms()
                # Сбрасывает охранный таймер
                self.resetWatchdog()
            except Exception, e:
                self.debug.send("Work error")
                self.debug.send(str(e))

# Обеспечивает работу в режиме приема СМС и передачи на пульт
class SmsRecieveWorker:
    # Конструктор
    def __init__(self, config):
        self.config = config

        self.speed = config.get(SER_SP)
        self.serial = core.Serial()        

        isDebug = config.get(DEBUG_SER) == "1"
        debugSpeed = config.get(DEBUG_SER_SP)
        debugBytetype = config.get(DEBUG_SER_OD)
        self.debug = core.Debug(isDebug, self.serial,
                                debugSpeed, debugBytetype)
        
        self.gsm = core.Gsm(config, self.serial, self.debug)
        self.gsm.simpleInit()
        
        self.recepientHelper = RecepientHelper(self.config, self.gsm, self.debug)
        # Хранилище для тревог
        self.alarms = {}
        self.alarmParser = AlarmParser()

        self.smsManager = core.SmsManager(self.gsm, self.debug)
        self.smsManager.initContext()
        self.smsReadTimer = 0
        self.resetSmsTimer()
                
        self.initWatchdog()

     # Сбрасывает таймер чтения СМС
    def resetSmsTimer(self):
        self.debug.send("Reset Sms Timer")
        self.smsReadTimer = MOD.secCounter() + int(self.config.get(SMS_READ_PERIOD))

    # Инициализирует охранный таймер
    def initWatchdog(self):
        MOD.watchdogEnable(int(self.config.get(WATCHDOG_PERIOD)))

    # Сбрасывает охранный таймер
    def resetWatchdog(self):
        MOD.watchdogReset()

    # Запускает
    def start(self):
        # Отсылает 10 раз 2 байта переинициализации
        self.debug.send("Start")
        for i in xrange(10):
            self.serial.sendbyte(0, self.speed, '8M1')
            self.serial.sendbyte(0, self.speed, '8E1')

        MOD.sleep(REBOOT_WAIT_TIMEOUT)

        self.recepients = self.recepientHelper.getRecepients()
        self.debug.send(str(self.recepients))
        self.work()

    # Обрабатывает SMS и возвращает описание тревоги
    def processSms(self, sms):
        self.debug.send("Process SMS")
        items = sms.text.split("-")
        if (len(items) < 2):
            self.debug.send("Wrong SMS format")
            return None

        codeStr = items[0].strip()
        try:
            code = int(codeStr)
            self.debug.send("Alarm code: " + codeStr)

            if code == CLAPAN_OPENED:
                if self.alarms.has_key(CLAPAN_CLOSED) == core.TRUE:
                    del self.alarms[CLAPAN_CLOSED]
            else:
                self.alarms[code] = core.TRUE
        except:
            return None

    # Отправляет тревогу с учётом чётности байта
    def sendAlarm(self, byte):
        if core.isOdd(byte) == core.TRUE:
            self.serial.sendbyte(byte, self.speed, "8O1")
        else:
            self.serial.sendbyte(byte, self.speed, "8E1")

    # Отправляет тревоги на пульт
    def sendAlarms(self):
        self.debug.send("Send alarms")
        keys = self.alarms.keys()
        self.debug.send(str(keys))
        alarms = self.alarmParser.encodeAlarmsToBups(keys)
        self.debug.send(str(alarms))

        # DATA2, DATA3, DATA4, DATA0        
        self.serial.sendbyte(BUPS_NETWORK, self.speed, "8M1")
        self.sendAlarm(alarms[1])            
        self.serial.sendbyte(BUPS_NETWORK, self.speed, "8M1")
        self.sendAlarm(alarms[2])            
        self.serial.sendbyte(BUPS_NETWORK, self.speed, "8M1")
        self.sendAlarm(alarms[3])
        self.serial.sendbyte(BUPS_NETWORK, self.speed, "8M1")
        self.sendAlarm(alarms[0])

        self.debug.send("Send alarms complete")

    # Основная работа
    def work(self):
        self.debug.send("Start work")
        while(core.TRUE):
            try:
                # Ожидает SMS
                if MOD.secCounter() > self.smsReadTimer:
                    self.debug.send("Get sms")
                    try:
                        smsList = self.smsManager.listSms()
                        for sms in smsList:
                            for recepient in self.recepients:
                                smsRec = sms.recepient.replace("+7", "8")
                                rec = recepient.replace("+7", "8")
                                if smsRec == rec:
                                    self.processSms(sms)
                    except:
                        pass

                    self.smsManager.deleteAll()
                    self.resetSmsTimer()
                
                # Отсылает 4 байта с тревогами на пульт(адрес пульта в INI)
                self.sendAlarms()
                self.resetWatchdog()
            except Exception, e:
                 self.debug.send(str(e))

try:
    settings = core.IniFile("settings.ini")
    settings.read()

    mode = settings.get(WORK_MODE)
    worker = None
    if mode == MASTER_GAS_MODE:
        worker = MasterGasWorker(settings)
    elif mode == BUPS_MODE:
        worker = BupsWorker(settings)
    elif mode == SMS_RECIEVE_MODE:
        worker = SmsRecieveWorker(settings)

    worker.start()
except Exception, e:
    import SER
    SER.set_speed("115200", "8N1")
    SER.send(e)
