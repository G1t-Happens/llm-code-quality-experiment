package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.LoginRequest;
import com.llmquality.baseline.dto.LoginResponse;
import com.llmquality.baseline.dto.UserRequest;
import com.llmquality.baseline.dto.UserResponse;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.UserMapper;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.UserService;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.List;


@Service
public class UserServiceImpl implements UserService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(UserServiceImpl.class);

    private static final String USER = "User";

    private final UserRepository userRepository;

    private final PasswordEncoder passwordEncoder;

    private final UserMapper userMapper;

    @Autowired
    public UserServiceImpl(final UserRepository userRepository, final PasswordEncoder passwordEncoder, final UserMapper userMapper) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.userMapper = userMapper;
    }

    @Override
    public List<UserResponse> listAll() {
        LOG.debug("--> listAll");
        final List<UserResponse> userResponses = userRepository.findAll().stream()
                .map(userMapper::toUserResponse)
                .toList();
        LOG.debug("<-- listAll, total users found: {}", userResponses.size());
        return userResponses;
    }

    @Override
    public UserResponse getById(final Long id) throws ResourceNotFoundException {
        LOG.debug("--> getById, id: {}", id);
        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, User with ID {} not found", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        final UserResponse userResponse = userMapper.toUserResponse(existingUserEntity);
        LOG.debug("<-- getById, user found: {}", userResponse.id());
        return userResponse;
    }

    @Override
    public UserResponse save(final UserRequest userRequest) throws ResourceAlreadyExistsException {
        LOG.debug("--> save, user with name: {}", userRequest.getName());

        if (userRepository.existsByName(userRequest.getName())) {
            LOG.error("<-- save, ResourceAlreadyExistsException for name: {}", userRequest.getName());
            throw new ResourceAlreadyExistsException(USER, "name", userRequest.getName());
        }

        final User userEntity = userMapper.toUserEntity(userRequest);
        userEntity.setPassword(passwordEncoder.encode(userEntity.getPassword()));

        final User savedUserEntity = userRepository.save(userEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- save, user saved with id: {}", savedUserEntity.getId());
        return userResponse;
    }

    @Override
    public UserResponse update(final Long id, final UserRequest userRequest) throws ResourceNotFoundException {
        LOG.debug("--> update, user with id: {}", id);

        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- update, User with ID {} not found for update", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userMapper.updateUserEntityFromUserRequest(userRequest, existingUserEntity);

        if (userRequest.getPassword() != null && !userRequest.getPassword().isBlank()) {
            existingUserEntity.setPassword(passwordEncoder.encode(userRequest.getPassword()));
        }

        final User savedUserEntity = userRepository.save(existingUserEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- update, user updated with id: {}", userResponse.id());
        return userResponse;
    }

    @Override
    public void delete(final Long id) throws ResourceNotFoundException {
        LOG.debug("--> delete, id: {}", id);

        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, User with ID {} not found for deletion", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userRepository.delete(existingUserEntity);
        LOG.debug("<-- delete, user with id {} deleted", id);
    }

    @Override
    public LoginResponse checkLogin(final LoginRequest loginRequest) throws ResourceNotFoundException {
        LOG.debug("--> checkLogin, name: {}", loginRequest.getName());

        final User existingUserEntity = userRepository.findByName(loginRequest.getName())
                .orElseThrow(() -> {
                    LOG.error("<-- checkLogin, User with name '{}' not found", loginRequest.getName());
                    return new ResourceNotFoundException(USER, "name", loginRequest.getName());
                });

        final boolean isPasswordCorrect = passwordEncoder.matches(loginRequest.getPassword(), existingUserEntity.getPassword());

        final LoginResponse loginResponse = new LoginResponse(isPasswordCorrect);

        LOG.debug("<-- checkLogin, login result for user '{}': {}", loginRequest.getName(), loginResponse.success());
        return loginResponse;
    }
}
