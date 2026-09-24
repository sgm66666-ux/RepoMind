public class DatabaseService {

    private String url;

    public void connect() {

        if(url.isEmpty()) {
            throw new RuntimeException("database url missing");
        }
    }
}
