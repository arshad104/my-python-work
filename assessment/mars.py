import simplejson as json
import os


class Mars(object):

    def __init__(self, data_directory=None):
        """
        Initialize object
        Set or Create a data directory
        """
        if data_directory is None:
            self.data_directory = os.path.join(
                os.path.dirname(__file__), 'data')
            if not os.path.exists(self.data_directory):
                os.mkdir(self.data_directory)
        elif not os.path.exists(data_directory):
            raise RuntimeError("Data dir [%s] does not exist" % data_directory)
        else:
            self.data_directory = data_directory
        self.file_path = os.path.join(self.data_directory, 'data.dat')

    def send(self, data):
        """
        (over)writes a JSON object to a file and returns 1 on success.
        Raises a general exception on error.
        """
        try:
            with open(self.file_path, 'wb') as data_file:
                json.dump(data, data_file)
        except Exception, e:
            raise RuntimeError('Failed to save data. Reason [%s]' % str(e))
        return 1

    def receive(self):
        """
        Reads a JSON object from a file and returns a dict on success.
        Raises a general exception on error.
        """
        try:
            with open(self.file_path, 'rb') as data_file:
                return json.load(data_file)
        except Exception, e:
            raise RuntimeError('Failed to read data. Reason [%s]' % str(e))


if __name__ == '__main__':
    data = dict(name="dubbizle", location="dubai")
    mars_obj = Mars()
    status = mars_obj.send(data)
    if status == 1:
        print '\nData sent to file : %s' % data
    rcv_data = mars_obj.receive()
    print '\nReceived data from file : %s' % rcv_data
