class Auth():

    def __init__(self, key_file):

        try:
           with open(key_file, 'r') as self.f:
            self.ff = self.f.read().split("\n")
        
            self.clientid = self.ff[0]
            self.clientsecret = self.ff[1]
            self.apikey = self.ff[2]
            
        except IOError:
            self.clientid = raw_input("Enter your clientID: ")
            self.clientsecret = raw_input("Enter your client secret: ")
            self.apikey = raw_input("Enter your API key: ")
            
    def writeAuth(self):
        self.auth = open('keys.txt', 'w')
        self.auth.write(clientid)
        self.auth.write(clientsecret)
        self.auth.write(apikey)
        self.auth.close()

    def getClientID(self):
        return self.clientid
    def getClientSecret(self):
        return self.clientsecret
    def getApiKey(self):
        return self.apikey
