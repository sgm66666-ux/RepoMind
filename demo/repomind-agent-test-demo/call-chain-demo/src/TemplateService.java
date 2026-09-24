public class TemplateService {

    private ConfigRepository repository;

    public String render() {
        String template = repository.getTemplate();
        return template.toUpperCase();
    }
}
