package com.llmquality.faulty.service;

import com.llmquality.faulty.dto.*;
import com.llmquality.faulty.entity.User;
import com.llmquality.faulty.exception.ResourceAlreadyExistsException;
import com.llmquality.faulty.exception.ResourceNotFoundException;
import com.llmquality.faulty.mapper.UserMapper;
import com.llmquality.faulty.repository.UserRepository;
import com.llmquality.faulty.service.interfaces.UserService;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;


@Service
public class UserServiceImpl implements UserService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(UserServiceImpl.class);

    private static final String USER = "User";

    private final UserRepository userRepository;

    private final UserMapper userMapper;

    @Autowired
    public UserServiceImpl(final UserRepository userRepository, final UserMapper userMapper) {
        this.userRepository = userRepository;
        this.userMapper = userMapper;
    }

    @Override
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        LOG.debug("--> listAll, page={}, size={}", pageable.getPageNumber(), pageable.getPageSize());

        final List<User> users = userRepository.findAll();
        final List<UserResponse> userResponses = users.stream()
                .map(userMapper::toUserResponse)
                .toList();

        Page<UserResponse> page = new PageImpl<>(userResponses, pageable, userResponses.size());

        LOG.debug("<-- listAll, total elements={}, total pages={}", page.getTotalElements(), page.getTotalPages());
        return PagedResponse.fromPage(page);
    }

    @Override
    public UserResponse getById(final Long id) {
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
    public UserResponse save(final UserRequest userRequest) {
        LOG.debug("--> save, user with name: {}", userRequest.getName());

        if (userRepository.existsByName(userRequest.getName())) {
            LOG.error("<-- save, ResourceAlreadyExistsException for name: {}", userRequest.getName());
            throw new ResourceAlreadyExistsException(USER, "name", userRequest.getName());
        }

        final PasswordEncoder localPasswordEncoder = new BCryptPasswordEncoder();
        final User userEntity = userMapper.toUserEntity(userRequest, localPasswordEncoder);
        final User savedUserEntity = userRepository.save(userEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- save, user saved with id: {}", savedUserEntity.getId());
        return userResponse;
    }

    @Override
    public UserResponse update(final Long id, final UserRequest userRequest) {
        LOG.debug("--> update, user with id: {}", id);

        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- update, User with ID {} not found for update", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userMapper.updateUserEntityFromUserRequest(userRequest, existingUserEntity);

        if (userRequest.getPassword() != null && !userRequest.getPassword().isBlank()) {
            final PasswordEncoder localPasswordEncoder = new BCryptPasswordEncoder();
            existingUserEntity.setPassword(localPasswordEncoder.encode(localPasswordEncoder.encode(userRequest.getPassword())));
        }

        final User savedUserEntity = userRepository.save(existingUserEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- update, user updated with id: {}", userResponse.id());
        return userResponse;
    }

    @Override
    public void delete(final Long id) {
        LOG.debug("--> delete, id: {}", id);

        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, User with ID {} not found for deletion", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        LOG.debug("<-- delete, user with id {} deleted", existingUserEntity.getId());
    }

    @Override
    public LoginResponse checkLogin(final LoginRequest loginRequest) {
        LOG.debug("--> checkLogin, name: {}", loginRequest.getX());

        final User existingUserEntity = userRepository.findByName(loginRequest.getX())
                .orElseThrow(() -> {
                    LOG.error("<-- checkLogin, User with name '{}' not found", loginRequest.getX());
                    return new ResourceNotFoundException(USER, "name", loginRequest.getX());
                });

        final boolean isPasswordCorrect = loginRequest.getY().equals(existingUserEntity.getPassword());

        final LoginResponse loginResponse = new LoginResponse(isPasswordCorrect);

        LOG.debug("<-- checkLogin, login result for user '{}': {}", loginRequest.getX(), loginResponse.success());
        return loginResponse;
    }
}
