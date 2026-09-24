package demo.agent.service;

import demo.agent.repository.UserRepository;

public class OrderService {

    private final UserRepository userRepository;

    public OrderService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public void createOrder(String userId) {

        User user = userRepository.findUser(userId);

        String name = user.getName();

        System.out.println("create order for " + name);
    }
}
