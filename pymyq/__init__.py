import requests
import logging


class MyQAPI:
    """Class for interacting with the MyQ iOS App API."""

    LIFTMASTER = 'liftmaster'
    CHAMBERLAIN = 'chamberlain'
    CRAFTSMAN = 'craftsman'
    MERLIN = 'merlin'

    SUPPORTED_BRANDS = [LIFTMASTER, CHAMBERLAIN, CRAFTSMAN, MERLIN]
    SUPPORTED_DEVICE_TYPE_NAMES = ['GarageDoorOpener', 'Garage Door Opener WGDO', 'VGDO', 'Gate']

    APP_ID = 'app_id'
    HOST_URI = 'myqexternal.myqdevice.com'

    BRAND_MAPPINGS = {
        LIFTMASTER: {
            APP_ID: 'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB/i'
        },
        CHAMBERLAIN: {
            APP_ID: 'OA9I/hgmPHFp9RYKJqCKfwnhh28uqLJzZ9KOJf1DXoo8N2XAaVX6A1wcLYyWsnnv'
        },
        CRAFTSMAN: {
            APP_ID: 'YmiMRRS1juXdSd0KWsuKtHmQvh5RftEp5iewHdCvsNB77FnQbY+vjCVn2nMdIeN8'
        },
        MERLIN: {
            APP_ID: '3004cac4e920426c823fa6c2ecf0cc28ef7d4a7b74b6470f8f0d94d6c39eb718'
        }
    }

    STATE_OPEN = 'open'
    STATE_CLOSED = 'closed'

    LOGIN_ENDPOINT = "api/v4/User/Validate"
    DEVICE_LIST_ENDPOINT = "api/v4/UserDeviceDetails/Get"
    DEVICE_SET_ENDPOINT = "api/v4/DeviceAttribute/PutDeviceAttribute"
    USERAGENT = "Chamberlain/3773 (iPhone; iOS 11.0.3; Scale/2.00)"

    REQUEST_TIMEOUT = 3.0

    DOOR_STATE = {
        '1': STATE_OPEN, #'open',
        '2': STATE_CLOSED, #'close',
        '3': STATE_OPEN, #'stopped',
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
            'password': self.password
        }

        try:
            login = requests.post(
                'https://{host_uri}/{login_endpoint}'.format(
                    host_uri=self.HOST_URI,
                    login_endpoint=self.LOGIN_ENDPOINT),
                    json=params,
                    headers={
                       'MyQApplicationId': self.BRAND_MAPPINGS[self.brand][self.APP_ID],
                       'User-Agent': self.USERAGENT
                    },
                    timeout=self.REQUEST_TIMEOUT
            )

            login.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            self.logger.error("MyQ - API Error[is_login_valid] %s", ex)
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

        try:
            devices = requests.get(
                'https://{host_uri}/{device_list_endpoint}'.format(
                    host_uri=self.HOST_URI,
                    device_list_endpoint=self.DEVICE_LIST_ENDPOINT),
                    headers={
                        'MyQApplicationId': self.BRAND_MAPPINGS[self.brand][self.APP_ID],
                        'SecurityToken': self.security_token,
                        'User-Agent': self.USERAGENT
                    }
            )

            devices.raise_for_status()
            
        except requests.exceptions.HTTPError as ex:
            self.logger.error("MyQ - API Error[get_devices] %s", ex)
            return False

        try:
            devices = devices.json()['Devices']
            return devices
        except KeyError:
            self.logger.error("MyQ - Login security token may have expired, will attempt relogin on next update")
            self._logged_in = False
        

    def get_garage_doors(self):
        """List only MyQ garage door devices."""
        devices = self.get_devices()

        if devices != False:
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
        else:
            return False;

    def get_status(self, device_id):
        """List only MyQ garage door devices."""
        devices = self.get_devices()

        garage_state = False

        if devices != False:
            for device in devices:
                if device['MyQDeviceTypeName'] in self.SUPPORTED_DEVICE_TYPE_NAMES and device['MyQDeviceId'] == device_id:
                    dev = {}
                    for attribute in device['Attributes']:
                        if attribute['AttributeDisplayName'] == 'doorstate':
                            myq_garage_state = attribute['Value']
                            garage_state = self.DOOR_STATE[myq_garage_state]
        
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
            'attributeName': 'desireddoorstate',
            'myQDeviceId': device_id,
            'AttributeValue': state,
        }

        try:
            device_action = requests.put(
                'https://{host_uri}/{device_set_endpoint}'.format(
                    host_uri=self.HOST_URI,
                    device_set_endpoint=self.DEVICE_SET_ENDPOINT),
                    data=payload,
                    headers={
                        'MyQApplicationId': self.BRAND_MAPPINGS[self.brand][self.APP_ID],
                        'SecurityToken': self.security_token,
                        'User-Agent': self.USERAGENT
                    }
            )

            device_action.raise_for_status()
        except (NameError, requests.exceptions.HTTPError) as ex:
            self.logger.error("MyQ - API Error[set_state] %s", ex)
            return False

        return device_action.status_code == 200
