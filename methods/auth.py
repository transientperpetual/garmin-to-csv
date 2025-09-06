import garth

def authenticate():

    try:
        #try to resume session
        garth.resume("~/.garth")
        garth.client.username
        print(f"Resumed session for {garth.client.username}")
    except:
        email = input("Enter email address: ")
        password = input("Enter password: ")

        try:
            garth.login(email, password)
            garth.save("~/.garth")
            print(f"Resumed session for {garth.client.username}")
        except Exception as e:
            print("Login failed.")
            print(e)

