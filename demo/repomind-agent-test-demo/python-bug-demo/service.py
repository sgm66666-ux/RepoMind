from repository import UserRepository

class UserService:

    def __init__(self):
        self.repo = UserRepository()

    def login(self, user_id):

        user = self.repo.get_user(user_id)

        return user["name"]
