import requests
import logging


class MyQAPI:
    """Class for interacting with the MyQ iOS App API."""

    LIFTMASTER = 'liftmaster'
    CHAMBERLAIN = 'chamberlain'
    CRAFTMASTER = 'craftmaster'

    SUPPORTED_BRANDS = [LIFTMASTER, CHAMBERLAIN, CRAFTMASTER]
    SUPPORTED_DEVICE_TYPE_NAMES = ['GarageDoorOpener', 'Garage Door Opener WGDO', 'VGDO']

    APP_ID = 'app_id'
    HOST_URI = 'host_uri'

    BRAND_MAPPINGS = {
        LIFTMASTER: {
            APP_ID: 'JVM/G9Nwih5BwKgNCjLxiFUQxQijAebyyg8QUHr7JOrP+tuPb8iHfRHKwTmDzHOu',
            HOST_URI: 'myqexternal.myqdevice.com'
        },
        CHAMBERLAIN: {
            APP_ID: 'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB%2Fi',
            HOST_URI: 'myqexternal.myqdevice.com'
        },
        CRAFTMASTER: {
            APP_ID: 'eU97d99kMG4t3STJZO/Mu2wt69yTQwM0WXZA5oZ74/ascQ2xQrLD/yjeVhEQccBZ',
            HOST_URI: 'craftexternal.myqdevice.com'
        }
    }

    STATE_OPEN = 'open'
    STATE_CLOSED = 'closed'

    LOCALE = "en"
    LOGIN_ENDPOINT = "api/user/validatewithculture"
    DEVICE_LIST_ENDPOINT = "api/v4/userdevicedetails/get"
    DEVICE_SET_ENDPOINT = "api/v4/DeviceAttribute/PutDeviceAttribute"
    HEADERS = {'User-Agent': 'Chamberlain/3773 (iPhone; iOS 10.0.1; Scale/2.00)'}

    REQUEST_TIMEOUT = 3.0

    DOOR_STATE = {
        '1': STATE_OPEN, #'open',
        '2': STATE_CLOSED, #'close',
        '4': STATE_OPEN, #'opening',
        '5': STATE_CLOSED, #'closing',
        '8': STATE_OPEN, #'in_transition',
        '9': STATE_OPEN, #'open'
    }

    logger = logging.getLogger(__name__)

    def __init__(self, username, password, brand):
        """Initialize the API object."""
        self.username = username
        self.password = password
        self.brand = brand
        self.security_token = None
        self._logged_in = False
        self._valid_brand = False

    def is_supported_brand(self):
        try:
            brand = self.BRAND_MAPPINGS[self.brand];
        except KeyError:
            return False

        return True

    def is_login_valid(self):
        """Log in to the MyQ service."""
        params = {
            'username': self.username,
            'password': self.password,
            'appId': self.BRAND_MAPPINGS[self.brand][self.APP_ID],
            'culture': self.LOCALE
        }

        try:
            login = requests.get(
                'https://{host_uri}/{login_endpoint}'.format(
                    host_uri=self.BRAND_MAPPINGS[self.brand][self.HOST_URI],
                    login_endpoint=self.LOGIN_ENDPOINT),
                    params=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT
            )

            login.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.logger.error("MyQ - API Error %s", ex)
            return False

        try:
            self.security_token = login.json()['SecurityToken']
        except KeyError:
            return False

        return True

    def get_devices(self):
        """List all MyQ devices."""
        if not self._logged_in:
            self._logged_in = self.is_login_valid()

        params = {
            'appId': self.BRAND_MAPPINGS[self.brand][self.APP_ID],
            'securityToken': self.security_token
        }

        try:
            devices = requests.get(
                'https://{host_uri}/{device_list_endpoint}'.format(
                    host_uri=self.BRAND_MAPPINGS[self.brand][self.HOST_URI],
                    device_list_endpoint=self.DEVICE_LIST_ENDPOINT),
                    params=params,
                    headers=self.HEADERS
            )

            devices.raise_for_status()

            devices = devices.json()['Devices']

            return devices
        except requests.exceptions.HTTPError as err:
            self.logger.error("MyQ - API Error %s", ex)
            return False

    def get_garage_doors(self):
        """List only MyQ garage door devices."""
        devices = self.get_devices()

        garage_doors = []

        try:
            for device in devices:
                if device['MyQDeviceTypeName'] in self.SUPPORTED_DEVICE_TYPE_NAMES:
                    dev = {}
                    for attribute in device['Attributes']:
                        if attribute['AttributeDisplayName'] == 'desc':
                            dev['deviceid'] = device['MyQDeviceId']
                            dev['name'] = attribute['Value']
                            garage_doors.append(dev)

            return garage_doors
        except TypeError:
            return False

    def get_status(self, device_id):
        """List only MyQ garage door devices."""
        devices = self.get_devices()

        for device in devices:
            if device['MyQDeviceTypeName'] in self.SUPPORTED_DEVICE_TYPE_NAMES and device['MyQDeviceId'] == device_id:
                dev = {}
                for attribute in device['Attributes']:
                   if attribute['AttributeDisplayName'] == 'doorstate':
                        garage_state = attribute['Value']

        garage_state = self.DOOR_STATE[garage_state]
        return garage_state

    def close_device(self, device_id):
        """Close MyQ Device."""
        return self.set_state(device_id, '0')

    def open_device(self, device_id):
        """Open MyQ Device."""
        return self.set_state(device_id, '1')

    def set_state(self, device_id, state):
        """Set device state."""
        payload = {
            'AttributeName': 'desireddoorstate',
            'MyQDeviceId': device_id,
            'ApplicationId': 'JVM/G9Nwih5BwKgNCjLxiFUQxQijAebyyg8QUHr7JOrP+tuPb8iHfRHKwTmDzHOu',
            'AttributeValue': state,
            'SecurityToken': self.security_token,
        }

        try:
            device_action = requests.put(
                'https://{host_uri}/{device_set_endpoint}'.format(
                    host_uri=self.BRAND_MAPPINGS[self.brand][self.HOST_URI],
                    device_set_endpoint=self.DEVICE_SET_ENDPOINT),
                    data=payload,
                    headers={
                        'MyQApplicationId': 'JVM/G9Nwih5BwKgNCjLxiFUQxQijAebyyg8QUHr7JOrP+tuPb8iHfRHKwTmDzHOu',
                        'SecurityToken': self.security_token
                    }
            )

            devices.raise_for_status()
        except (NameError, requests.exceptions.HTTPError) as ex:
            self.logger.error("MyQ - API Error %s", ex)
            return False

        return device_action.status_code == 200

