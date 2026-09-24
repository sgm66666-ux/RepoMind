public class EmailService {

    private TemplateService templateService;

    public void sendEmail(String email) {
        String content = templateService.render();
        System.out.println(content);
    }
}
