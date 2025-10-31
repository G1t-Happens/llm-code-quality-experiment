package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.LoginRequest;
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
import java.util.Optional;


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
                .orElseThrow(() -> new ResourceNotFoundException(USER, "id", id));
        final UserResponse userResponse = userMapper.toDTO(user);
        LOG.debug("<-- getById, user found: {}", userResponse.getId());
        return userResponse;
    }

    @Override
    public UserResponse save(final UserRequest userRequest) throws ResourceAlreadyExistsException {
        LOG.debug("--> save, user with name: {}", userRequest.getName());

        if (userRepository.existsByName(userRequest.getName())) {
            LOG.debug("<-- save, ResourceAlreadyExistsException for name: {}", userRequest.getName());
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
                .orElseThrow(() -> new ResourceNotFoundException(USER, "id", id));

        userMapper.updateEntityFromDto(userRequest, existingEntity);

        if (userRequest.getPassword() != null && !userRequest.getPassword().isBlank()) {
            existingEntity.setPassword(passwordEncoder.encode(userRequest.getPassword()));
        }

        final User savedEntity = userRepository.save(existingEntity);
        final UserResponse userResponse = userMapper.toDTO(savedEntity);

        LOG.debug("<-- update, user updated with id: {}", userResponse.getId());
        return userResponse;
    }

    @Override
    public void delete(final Long id) throws ResourceNotFoundException {
        LOG.debug("--> delete, id: {}", id);

        final User entity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.debug("<-- delete, User with ID {} not found for deletion", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        userRepository.delete(entity);
        LOG.debug("<-- delete, user with id {} deleted", id);
    }

    @Override
    public boolean checkLogin(final LoginRequest loginRequest) {
        LOG.debug("--> checkLogin, name: {}", loginRequest.getName());

        final Optional<User> userOptional = findUserByName(loginRequest.getName());

        if (userOptional.isEmpty()) {
            LOG.debug("<-- checkLogin, user not found for name: {}", loginRequest.getName());
            return false;
        }

        final User user = userOptional.get();
        final boolean valid = validatePassword(loginRequest.getPassword(), user.getPassword());

        LOG.debug("<-- checkLogin, login result: {}", valid);
        return valid;
    }

    /**
     * Finds a user by their username.
     * <p>
     * This method searches for users with the specified username and returns the first
     * user found, if any. Since usernames are expected to be unique, the result is
     * typically either an empty {@link Optional} or contains a single user.
     * </p>
     *
     * @param name the username to search for; must not be {@code null} or empty
     * @return an {@link Optional} containing the found user, or an empty {@link Optional} if no user is found
     */
    private Optional<User> findUserByName(final String name) {
        return userRepository.findByName(name).stream().findFirst();
    }

    /**
     * Validates whether the provided plain text password matches the stored (encoded) password.
     * <p>
     * This method compares the raw password with the encoded password stored in the system
     * to check for a match using the configured password encoder.
     * </p>
     *
     * @param rawPassword     the plain text password to validate
     * @param encodedPassword the encoded password stored in the system
     * @return {@code true} if the raw password matches the encoded password, {@code false} otherwise
     */
    private boolean validatePassword(final String rawPassword, final String encodedPassword) {
        return passwordEncoder.matches(rawPassword, encodedPassword);
    }
}
