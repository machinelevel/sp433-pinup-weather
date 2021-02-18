"""
Secret Plan #433: Pinup Weather
by Eric and Sue Johnston, inventions@machinelevel.com
25 Jan 2021

This program was written for the Adafruit Feather
with 2.9" grayscale ans ESP Wifi
...and then it was migrated to MagTag

License:
    Officially: MIT license
    This software is free (like free speech AND free beer)
    Do anything you like with this, but please use it for good.
    If you use it, drop us a note and say hi!
    There is no warranty at all, use at your own risk.

my notes:
# deep sleep: https://learn.adafruit.com/deep-sleep-with-circuitpython
# best magtag wifi sample: https://learn.adafruit.com/magtag-progress-displays?view=all
# sleep notes here: https://learn.adafruit.com/deep-sleep-with-circuitpython/alarms-and-sleep
"""

is_magtag = True
use_magtag_lib = False

import time
import adafruit_imageload

import busio
import board
import analogio
import gc
import neopixel
if is_magtag:
    import ipaddress
    import ssl
    import wifi
    import socketpool
    import adafruit_requests
else:
    import adafruit_il0373
    import adafruit_esp32spi.adafruit_esp32spi_socket as socket
    from adafruit_esp32spi import adafruit_esp32spi
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    import adafruit_requests as requests

from digitalio import DigitalInOut
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

import displayio
if not is_magtag:
    displayio.release_displays()

zipcode = '02210' # This is the zip code it will report weather for

def main():
    ink = Ink()
    ink.draw_all(None)
    weather = NetWeather()
    time.sleep(1)
    while 1:
        weather.fetch_weather()
        pixels[0] = (0,0,0)
        ink.draw_all(weather)
        time.sleep(15 * 60)


class Ink:
    def __init__(self):
        print('initializing ink...')
        self.batt_pin = analogio.AnalogIn(board.VOLTAGE_MONITOR)
        self.icon_table = {
            '01d':8, '01n':0, #     clear sky
            '02d':7, '02n':6, #     few clouds
            '03d':7, '03n':6, #     scattered clouds
            '04d':6, '04n':6, #     broken clouds
            '09d':5, '09n':5, #     shower rain
            '10d':5, '10n':5, #     rain
            '11d':4, '11n':4, #     thunderstorm
            '13d':3, '13n':3, #     snow
            '50d':2, '50n':2, #     mist
        }

        if is_magtag:
            self.display = board.DISPLAY
            time.sleep(self.display.time_to_refresh)
            while self.display.busy:
                time.sleep(0.5)
        else:
            epd_cs = board.D9
            epd_dc = board.D10
            display_bus = displayio.FourWire(
                spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
            )
            time.sleep(1)
            self.display = adafruit_il0373.IL0373(
                display_bus,
                width=296,
                height=128,
                rotation=270,
                black_bits_inverted=False,
                color_bits_inverted=False,
                grayscale=True,
                refresh_time=1,
            )


        f = open("/images/pin2e.bmp", "rb")
        self.pinback1 = displayio.OnDiskBitmap(f)
        self.numbers22 = self.numbers_from_bmp('/images/numbers22x165.bmp', '-0123456789', [0,8,25,40,56,71,87,103,118,134,149,165])
        self.numbers17 = self.numbers_from_bmp('/images/numbers17x127.bmp', '-0123456789', [0,6,19,31,43,54,67, 79, 91,103,114,127])
        self.numbers11 = self.numbers_from_bmp('/images/numbers11x82.bmp',  '-0123456789', [0,3,12,19,28,34,43, 50, 58, 66, 73, 81])
        self.weekdays11 = self.numbers_from_bmp('/images/weekdays11x174.bmp', '0123456', [0,31,55,83,112,131,155,174])
        self.months11 = self.numbers_from_bmp('/images/months11x294.bmp', '0123456789abc', [0,0,22,44,73,98,126,149,170,197,220,244,272,294])
        self.batt20 = self.numbers_from_bmp('/images/batt20x118.bmp', '0xyz2c', [0,28,37,38,58,87,118])
        self.wicons40 = self.numbers_from_bmp('/images/wicons40x347.bmp', '012345678', [0,346-312,346-276,346-241,346-203,346-160,346-121,346-82,346-38,346-0])
        self.palette1 = displayio.Palette(4)
        self.palette1[0] = 0x000000
        self.palette1[1] = 0x606060
        self.palette1[2] = 0x909090
        self.palette1[3] = 0xffffff
        self.palette1.make_transparent(3)
        print('initialized ink ok.')

#        t8 = tile_from_bmp('/images/icon_suncloud64_8.bmp')

    def draw_all(self, weather):
        print('drawing...')
        g = displayio.Group(max_size=30)
        g.append(displayio.TileGrid(self.pinback1, pixel_shader=displayio.ColorConverter()))

#        show_current_temp = -8
#        show_feels_like_temp = -12
        if weather is not None:
            self.draw_number(weather.show_current_temp, 140, 80, self.numbers22, g)
            self.draw_number(weather.show_feels_like_temp, 116, 90, self.numbers17, g)
            x = 12
            y = 64
            y = self.draw_number(weather.updated_hour, x, y, self.numbers11, g)
            y = self.draw_number(weather.updated_minute, x, y + 5, self.numbers11, g, pad0=True)
            x = 1
            y = 64
            y = self.draw_index([weather.updated_weekday], x, y + 5, self.weekdays11, g)
            if 0:
                y = self.draw_index([weather.updated_month], x, y + 5, self.months11, g)
                y = self.draw_number(weather.updated_monthday, x, y + 5, self.numbers11, g)

            x = 50
            y = 2
            y = self.draw_weather_icon(x, y, weather, g)

            x = 40
            y = 70
            y = self.draw_wind(x, y, weather, g)

        self.draw_battery_level(g)

        self.display.show(g)
        self.refresh()
        print('  ...draw done.')
        g = None
        gc.collect()

    def refresh(self):
        self.display.refresh()
        time.sleep(self.display.time_to_refresh)
        while self.display.busy:
            time.sleep(0.5)

    def draw_weather_icon(self, x, y, weather, g):
        if weather is not None:
            if weather.show_icon in self.icon_table:
                icon_index = self.icon_table[weather.show_icon]
                y = self.draw_index([icon_index], x, y, self.wicons40, g)
        return y

    def draw_wind(self, x, y, weather, g):
        if weather is not None:
            if weather.show_wind_mph >= 2:
                y = self.draw_index([1], x, y, self.wicons40, g)
                y = self.draw_number(weather.show_wind_mph, x+5, y-2, self.numbers17, g)
        return y

    def draw_battery_level(self, g):
        # Voltages observed:
        # 2.66 = out of gas, shut down
        # 4.21 is all charged and plugged in
        battery_voltage = (self.batt_pin.value * 3.3) / 65536 * 2
        print("VBat voltage: {:.2f}".format(battery_voltage))
        x = 0
        y = 0
        batt_low = 0
        batt_fill = 2
        t = (battery_voltage - 2.9) / (4.2 - 2.9)
        if t > 1.0:
            t = 1.0
        fill_count = round(16 * t)
        self.draw_index([batt_low], x, y, self.batt20, g)
        for fillpos in range(fill_count):
            self.draw_index([batt_fill], x, y+7+fillpos, self.batt20, g) #14 segs?
        if 0:
            y = self.draw_number(int(battery_voltage * 100), x, y + 5, self.numbers11, g)


    def draw_number(self, val, x, y, font, group, pad0=False):        
        if val is not None:
            strval = str(val)
            if pad0 and val < 10:
                strval = '0' + strval
            for ch in str(val):
                bm = font[ch]
                tile = displayio.TileGrid(bm, pixel_shader=self.palette1, x=x, y=y)
                group.append(tile)
                y += bm.height
        return y

    def draw_index(self, val, x, y, font, group):
        if val is not None:
            for i in val:
                bm = font[i]
                tile = displayio.TileGrid(bm, pixel_shader=self.palette1, x=x, y=y)
                group.append(tile)
                y += bm.height
        return y

    def tile_from_bmp(self, file_name):
        dbm, dpal = adafruit_imageload.load(file_name,
                                            bitmap=displayio.Bitmap,
                                            palette=displayio.Palette)
        bm = displayio.Bitmap(dbm.width, dbm.height, 4)
        for y in range(dbm.height):
            for x in range(dbm.width):
                bm[x, y] = self.gray_256_to_4(dpal[dbm[x, y]] & 0x00ff)
        dbm = None
        dpal = None
        gc.collect()
        return bm

    def gray_256_to_4(self, p):
        if p < 0x60:
            return 0
        elif p < 0x90:
            return 1
        elif p < 0xff:
            return 2
        return 3

    def numbers_from_bmp(self, file_name, symbols, markers):
        dbm, dpal = adafruit_imageload.load(file_name,
                                            bitmap=displayio.Bitmap,
                                            palette=displayio.Palette)
        numbers = {}
        # a = 0
        # b = markers[0]
        # bm = displayio.Bitmap(dbm.width, b - a, 4)
        # for y in range(bm.height):
        #     for x in range(bm.width):
        #         bm[x, y] = self.gray_256_to_4(dpal[dbm[x, y]] & 0x00ff)
        # numbers['-'] = numbers[-1] = bm
        for index,symbol in enumerate(symbols):
            a = markers[index]
            b = markers[index + 1]
            bm = displayio.Bitmap(dbm.width, b - a, 4)
            for y in range(bm.height):
                for x in range(bm.width):
                    bm[x, y] = self.gray_256_to_4(dpal[dbm[x, y + a]] & 0x00ff)
            numbers[symbol] = numbers[index] = bm

        dbm = None
        dpal = None
        gc.collect()
        return numbers

# Magtag pins:
# ['__class__', 'A1', 'A3', 'ACCELEROMETER_INTERRUPT', 'AD1', 'BATTERY', 
# 'BUTTON_A', 'BUTTON_B', 'BUTTON_C', 'BUTTON_D', 'CS', 'D1', 'D10', 'D11', 
# 'D12', 'D13', 'D14', 'D15', 'DISPLAY', 'EPD_BUSY', 'EPD_CS', 'EPD_DC', 
# 'EPD_RESET', 'I2C', 'LIGHT', 'MISO', 'MOSI', 'NEOPIXEL', 'NEOPIXEL_POWER', 
# 'SCK', 'SCL', 'SDA', 'SPEAKER', 'SPEAKER_ENABLE', 'SPI', 'VOLTAGE_MONITOR']
"""
board.A1 board.AD1
board.A3 board.LIGHT
board.ACCELEROMETER_INTERRUPT
board.BATTERY board.VOLTAGE_MONITOR
board.BUTTON_A board.D15
board.BUTTON_B board.D14
board.BUTTON_C board.D12
board.BUTTON_D board.D11
board.CS board.EPD_CS
board.D1 board.NEOPIXEL
board.D10
board.D13
board.EPD_BUSY
board.EPD_DC
board.EPD_RESET
board.MISO
board.MOSI
board.NEOPIXEL_POWER
board.SCK
board.SCL
board.SDA
board.SPEAKER
board.SPEAKER_ENABLE
"""

class NetWeather:
    def __init__(self):
        print('initializing weather...')
        print(dir(board))
        self.show_current_temp = 0
        self.show_feels_like_temp = 0
        self.updated_hour = 0
        self.updated_minute = 0
        self.updated_weekday = 0
        self.updated_month = 1
        self.updated_monthday = 0
        self.show_icon = None
        self.show_wind_mph = 0

        if is_magtag:
            self.radio = wifi.radio

            if 0:
                print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])
                print("Available WiFi networks:")
                for network in wifi.radio.start_scanning_networks():
                    print("\t%s\t\tRSSI: %d\tChannel: %d" % (str(network.ssid, "utf-8"),
                            network.rssi, network.channel))
                wifi.radio.stop_scanning_networks()
             
            print("Connecting to %s"%secrets["ssid"])
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            print("Connected to %s!"%secrets["ssid"])
            print("My IP address is", wifi.radio.ipv4_address)

            if 0:
                ipv4 = ipaddress.ip_address("8.8.4.4")
                print("Ping google.com: %f ms" % (wifi.radio.ping(ipv4)*1000))
             
            pool = socketpool.SocketPool(wifi.radio)
            self.requests = adafruit_requests.Session(pool, ssl.create_default_context())

        else:
            esp32_cs = DigitalInOut(board.D13)
            esp32_ready = DigitalInOut(board.D11)
            esp32_reset = DigitalInOut(board.D12)
            self.radio = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
            requests.set_socket(socket, self.radio)
            self.requests = requests
            if self.radio.status == adafruit_esp32spi.WL_IDLE_STATUS:
                print("ESP32 found and in idle mode")
            print("Firmware vers.", self.radio.firmware_version)
            print("MAC addr:", [hex(i) for i in self.radio.MAC_address])
            for ap in self.radio.scan_networks():
                print("\t%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

            print("Connecting to AP...")
            while not self.radio.is_connected:
                try:
                    self.radio.connect_AP(secrets["ssid"], secrets["password"])
                except RuntimeError as e:
                    print("could not connect to AP, retrying: ", e)
                    continue
            print("Connected to", str(self.radio.ssid, "utf-8"), "\tRSSI:", self.radio.rssi)
            print("My IP address is", self.radio.pretty_ip(self.radio.ip_address))

    def fetch_text(self, url):
        r = self.requests.get(url)
        result = r.text
        r.close()
        return result

    def fetch_json(self, url):
        r = self.requests.get(url)
        result = r.json()
        r.close()
        return result

    def fetch_weather(self):
        gc.collect()
        time_url = "http://worldtimeapi.org/api/ip"
        print('fetching weather now...')
        weather_now_url = 'http://api.openweathermap.org/data/2.5/weather?zip={},us&units=metric&appid={}'.format(zipcode, secrets['openweather_apikey'])
        try:
            wnow = self.fetch_json(weather_now_url)
            tzone = wnow['timezone']
            lat = wnow['coord']['lat']
            lon = wnow['coord']['lon']
            timezone = wnow['timezone']
            time_now = time.localtime(wnow['dt'] + timezone)
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            print('It\'s {}:{} on {}'.format(time_now.tm_hour, time_now.tm_min, days[time_now.tm_wday]))
            print('Weather in {}:'.format(wnow['name']))
            print('  temp: {}'.format(round(wnow['main']['temp'])))
            print('  feels-like: {}'.format(round(wnow['main']['feels_like'])))
            print('    {}'.format(wnow['weather'][0]['description']))
            print('  wind: {} mph'.format(round(0.621371 * wnow['wind']['speed'])))
            self.show_current_temp = round(wnow['main']['temp'])
            self.show_feels_like_temp = round(wnow['main']['feels_like'])
            self.show_icon = wnow['weather'][0]['icon']
            self.show_wind_mph = round(0.621371 * wnow['wind']['speed'])
            self.updated_hour = time_now.tm_hour
            self.updated_minute = time_now.tm_min
            self.updated_weekday = time_now.tm_wday
            self.updated_month = time_now.tm_mon
            self.updated_monthday =time_now.tm_mday

            print('fetching hourly forecast...')
            weather_one_url = 'http://api.openweathermap.org/data/2.5/onecall?lat={}&lon={}&units=metric&appid={}'.format(lat, lon, secrets['openweather_apikey'])
            wone = self.fetch_json(weather_one_url)
            hourly = wone['hourly']
            for item in hourly:
                hourly_time = time.localtime(item['dt'] + timezone)
                out_str = '  {}:{} on {}:'.format(hourly_time.tm_hour, hourly_time.tm_min, days[hourly_time.tm_wday])
                out_str += ' {}/{}'.format(item['temp'], item['feels_like'])
                out_str += ' {}'.format(item['weather'][0]['description'])
                print(out_str)
        except:
            print('failed to get weather forecast')

        wnow = None
        wone = None
        gc.collect()

        # # https://openweathermap.org/api
        # WEATHER_API = 'http://api.openweathermap.org/data/2.5/weather?zip=02210,us&units=metric&appid=' + secrets['openweather_apikey']
        # sample_result = {"coord":{"lon":-71.0465,"lat":42.3489},
        #                  "weather":[{"id":802,
        #                              "main":"Clouds",
        #                              "description":"scattered clouds",
        #                              "icon":"03d"}],
        #                  "base":"stations",
        #                  "main":{"temp":-1.11,
        #                          "feels_like":-11.05,
        #                          "temp_min":-2,
        #                          "temp_max":-0.56,
        #                          "pressure":1013,
        #                          "humidity":29},
        #                  "visibility":10000,
        #                  "wind":{"speed":9.26,"deg":290,"gust":16.46},
        #                  "clouds":{"all":40},
        #                  "dt":1611521329,
        #                  "sys":{"type":1,"id":3486,"country":"US","sunrise":1611489890,"sunset":1611524854},
        #                  "timezone":-18000,"id":0,"name":"Boston","cod":200}
        # #dt+timezone struct_time(tm_year=2021, tm_mon=1, tm_mday=25, tm_hour=18, tm_min=11, tm_sec=22, tm_wday=0, tm_yday=25, tm_isdst=-1)

        # Icon codes
        # day         night
        # 01d.png     01n.png     clear sky
        # 02d.png     02n.png     few clouds
        # 03d.png     03n.png     scattered clouds
        # 04d.png     04n.png     broken clouds
        # 09d.png     09n.png     shower rain
        # 10d.png     10n.png     rain
        # 11d.png     11n.png     thunderstorm
        # 13d.png     13n.png     snow
        # 50d.png     50n.png     mist


main()
