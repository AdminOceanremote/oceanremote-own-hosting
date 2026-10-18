from django import template

register = template.Library()

@register.filter(name='is_special_device')
def is_special_device(device_id):
    """
    Custom filter to check if a device ID is special.
    """
    special_devices = ['device1', 'device2', 'device3', 'device4', 'device5', 'device6']
    return device_id in special_devices