import os


class Auth():

    def __init__(self, key_file):
        try:
            with open(key_file, 'r') as self.f:
                self.clientid = self.f.readline()
                self.clientsecret = self.f.readline()
                self.apikey = self.f.readline()
        except IOError:
            self.clientid = raw_input("Enter your clientID: ")
            self.clientsecret = raw_input("Enter your client secret: ")
            self.apikey = raw_input("Enter your API key: ")
            self.write_auth()
            
    def write_auth(self):
        with open(os.environ['HOME'] + '/.tasky/keys.txt', 'w') as self.auth:
            self.auth.write(str(self.clientid) + '\n')
            self.auth.write(str(self.clientsecret) + '\n')
            self.auth.write(str(self.apikey) + '\n')

    def get_client_ID(self):
        return self.clientid

    def get_client_secret(self):
        return self.clientsecret

    def get_API_key(self):
        return self.apikey
