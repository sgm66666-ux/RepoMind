public class UserService {

    private EmailService emailService;

    public void register(String email) {
        emailService.sendEmail(email);
    }
}
