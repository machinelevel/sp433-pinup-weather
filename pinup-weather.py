"""
Secret Plan #433: Pinup Weather
by Eric and Sue Johnston, inventions@machinelevel.com
25 Jan 2021

This program was written for the Adafruit Feather
with 2.9" grayscale ans ESP Wifi

License:
    Officially: MIT license
    This software is free (like free speech AND free beer)
    Do anything you like with this, but please use it for good.
    If you use it, drop us a note and say hi!
    There is no warranty at all, use at your own risk.

my notes:
# deep sleep: https://learn.adafruit.com/deep-sleep-with-circuitpython
  """
 
import time
import busio
import board
import displayio
import adafruit_il0373
import gc
import neopixel
import adafruit_imageload

import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
from digitalio import DigitalInOut
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

displayio.release_displays()
# This pinout works on a Feather M4 and may need to be altered for other boards.
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
zipcode = '02210' # This is the zip code it will report weather for
show_current_temp = None
show_feels_like_temp = None

def main():
    ink = Ink()
    ink.draw_all()
    time.sleep(1)
    weather = NetWeather()
    time.sleep(1)
    while 1:
        weather.fetch_weather()
        ink.draw_all()
        time.sleep(30 * 60)


class Ink:
    def __init__(self):
        print('initializing ink...')
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


        f = open("/images/pin2c.bmp", "rb")
        pic = displayio.OnDiskBitmap(f)
        self.pinback1 = displayio.TileGrid(pic, pixel_shader=displayio.ColorConverter())
        self.numbers22 = numbers_from_bmp('/images/numbers22x165.bmp', 8, 15)
        self.numbers17 = numbers_from_bmp('/images/numbers17x127.bmp', 6, 12)
        self.numbers11 = numbers_from_bmp('/images/numbers11x82.bmp', 2, 8)

#        t8 = tile_from_bmp('/images/icon_suncloud64_8.bmp')

    def draw_all(self):
        g = displayio.Group()
        g.append(self.pinback1)

        self.draw_number(show_current_temp, 50, 50, self.numbers22, g)

        self.display.show(g)
        self.display.refresh()
        g = None
        gc.collect()

    def draw_number(self, val, x, y, font, group):
#        if val is not None:
        group.append(font[2])




class NetWeather:
    def __init__(self):
        print('initializing weather...')
        esp32_cs = DigitalInOut(board.D13)
        esp32_ready = DigitalInOut(board.D11)
        esp32_reset = DigitalInOut(board.D12)
        self.esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
        requests.set_socket(socket, self.esp)
        if self.esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
            print("ESP32 found and in idle mode")
        print("Firmware vers.", self.esp.firmware_version)
        print("MAC addr:", [hex(i) for i in self.esp.MAC_address])
        for ap in self.esp.scan_networks():
            print("\t%s\t\tRSSI: %d" % (str(ap["ssid"], "utf-8"), ap["rssi"]))

        print("Connecting to AP...")
        while not self.esp.is_connected:
            try:
                self.esp.connect_AP(secrets["ssid"], secrets["password"])
            except RuntimeError as e:
                print("could not connect to AP, retrying: ", e)
                continue
        print("Connected to", str(self.esp.ssid, "utf-8"), "\tRSSI:", self.esp.rssi)
        print("My IP address is", self.esp.pretty_ip(self.esp.ip_address))

    def fetch_text(self, url):
        r = requests.get(url)
        result = r.text
        r.close()
        return result

    def fetch_json(self, url):
        r = requests.get(url)
        result = r.json()
        r.close()
        return result

    def fetch_weather(self):
        gc.collect()
        time_url = "http://worldtimeapi.org/api/ip"
        print('fetching weather now...')
        weather_now_url = 'http://api.openweathermap.org/data/2.5/weather?zip={},us&units=metric&appid={}'.format(zipcode, secrets['openweather_apikey'])
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

        show_current_temp = round(wnow['main']['temp'])
        show_feels_like_temp = round(wnow['main']['feels_like'])

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

def tile_from_bmp(file_name):
    pal7 = displayio.Palette(4)
    pal7[0] = 0x000000
    pal7[1] = 0x606060
    pal7[2] = 0x909090
    pal7[3] = 0xffffff
    pal7.make_transparent(3)
    dbm, dpal = adafruit_imageload.load(file_name,
                                        bitmap=displayio.Bitmap,
                                        palette=displayio.Palette)
    bm = displayio.Bitmap(dbm.width, dbm.height, 4)
    for y in range(dbm.height):
        for x in range(dbm.width):
            bm[x, y] = gray_256_to_4(dpal[dbm[x, y]] & 0x00ff)
    dbm = None
    dpal = None
    gc.collect()
    return displayio.TileGrid(bm, pixel_shader=pal7)

def gray_256_to_4(p):
    if p < 0x60:
        return 0
    elif p < 0x90:
        return 1
    elif p < 0xff:
        return 2
    return 3

def numbers_from_bmp(file_name, minus_width, digit_width):
    pal7 = displayio.Palette(4)
    pal7[0] = 0x000000
    pal7[1] = 0x606060
    pal7[2] = 0x909090
    pal7[3] = 0xffffff
    pal7.make_transparent(3)
    dbm, dpal = adafruit_imageload.load(file_name,
                                        bitmap=displayio.Bitmap,
                                        palette=displayio.Palette)
    numbers = {}
    bm = displayio.Bitmap(dbm.width, minus_width, 4)
    for y in range(bm.height):
        for x in range(bm.width):
            bm[x, y] = gray_256_to_4(dpal[dbm[x, y]] & 0x00ff)
    numbers['-'] = numbers[-1] = displayio.TileGrid(bm, pixel_shader=pal7)
    for digit in range(10):
        bm = displayio.Bitmap(dbm.width, digit_width, 4)
        for y in range(bm.height):
            for x in range(bm.width):
                bm[x, y] = gray_256_to_4(dpal[dbm[x, y + digit * digit_width + minus_width]] & 0x00ff)
        numbers[str(digit)] = numbers[digit] = displayio.TileGrid(bm, pixel_shader=pal7)

    dbm = None
    dpal = None
    gc.collect()
    return numbers

main()
