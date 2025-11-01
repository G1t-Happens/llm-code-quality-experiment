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
                .map(userMapper::toDTO)
                .toList();
        LOG.debug("<-- listAll, total users found: {}", userResponses.size());
        return userResponses;
    }

    @Override
    public UserResponse getById(final Long id) throws ResourceNotFoundException {
        LOG.debug("--> getById, id: {}", id);
        final User user = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, User with ID {} not found", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        final UserResponse userResponse = userMapper.toDTO(user);
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

        final User entity = userMapper.toEntity(userRequest);
        entity.setPassword(passwordEncoder.encode(entity.getPassword()));

        final User savedEntity = userRepository.save(entity);
        final UserResponse userResponse = userMapper.toDTO(savedEntity);

        LOG.debug("<-- save, user saved with id: {}", savedEntity.getId());
        return userResponse;
    }

    @Override
    public UserResponse update(final Long id, final UserRequest userRequest) throws ResourceNotFoundException {
        LOG.debug("--> update, user with id: {}", id);

        final User existingEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- update, User with ID {} not found for update", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userMapper.updateEntityFromDto(userRequest, existingEntity);

        if (userRequest.getPassword() != null && !userRequest.getPassword().isBlank()) {
            existingEntity.setPassword(passwordEncoder.encode(userRequest.getPassword()));
        }

        final User savedEntity = userRepository.save(existingEntity);
        final UserResponse userResponse = userMapper.toDTO(savedEntity);

        LOG.debug("<-- update, user updated with id: {}", userResponse.id());
        return userResponse;
    }

    @Override
    public void delete(final Long id) throws ResourceNotFoundException {
        LOG.debug("--> delete, id: {}", id);

        final User user = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, User with ID {} not found for deletion", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userRepository.delete(user);
        LOG.debug("<-- delete, user with id {} deleted", id);
    }

    @Override
    public LoginResponse checkLogin(final LoginRequest loginRequest) throws ResourceNotFoundException {
        LOG.debug("--> checkLogin, name: {}", loginRequest.getName());

        final User user = userRepository.findByName(loginRequest.getName())
                .orElseThrow(() -> {
                    LOG.error("<-- checkLogin, User with name '{}' not found", loginRequest.getName());
                    return new ResourceNotFoundException(USER, "name", loginRequest.getName());
                });

        final boolean valid = passwordEncoder.matches(loginRequest.getPassword(), user.getPassword());

        final LoginResponse loginResponse = new LoginResponse(valid);

        LOG.debug("<-- checkLogin, login result for user '{}': {}", loginRequest.getName(), loginResponse.success());
        return loginResponse;
    }
}
