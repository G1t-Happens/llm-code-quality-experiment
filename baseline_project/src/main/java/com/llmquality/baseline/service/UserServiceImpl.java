package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.enums.Role;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.exception.UnauthorizedException;
import com.llmquality.baseline.mapper.UserMapper;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.UserService;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Objects;


@Service
@Transactional(readOnly = true)
public class UserServiceImpl implements UserService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(UserServiceImpl.class);

    private static final String USER = "User";

    // Prevent timing attack (username enumeration) by always performing password comparison
    private static final String DUMMY_HASH = "$2a$10$dummydummydummydummydummydummydummydummydummydummy";

    private final UserRepository userRepository;

    private final PasswordEncoder passwordEncoder;

    private final UserMapper userMapper;

    private final JwtEncoder jwtEncoder;

    @Value("${jwt.issuer:self}")
    private String jwtIssuer;

    @Value("${jwt.expiration-hours:6}")
    private long jwtExpirationHours;

    @Autowired
    public UserServiceImpl(UserRepository userRepository, PasswordEncoder passwordEncoder, UserMapper userMapper, JwtEncoder jwtEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.userMapper = userMapper;
        this.jwtEncoder = jwtEncoder;
    }

    @Override
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        LOG.debug("--> listAll, page={}, size={}", pageable.getPageNumber(), pageable.getPageSize());
        final Page<UserResponse> page = userRepository.findAll(pageable).map(userMapper::toUserResponse);
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
    public UserResponse getByUsername(final String username) {
        LOG.debug("--> getByUsername, username: {}", username);

        final User existingUserEntity = userRepository.findByUsername(username)
                .orElseThrow(() -> {
                    LOG.error("<-- getByUsername, User '{}' not found", username);
                    return new ResourceNotFoundException(USER, "username", username);
                });

        final UserResponse userResponse = userMapper.toUserResponse(existingUserEntity);
        LOG.debug("<-- getByUsername, user found: {}", userResponse.id());
        return userResponse;
    }

    @Transactional
    @Override
    public UserResponse save(final UserRequest userRequest) {
        LOG.debug("--> save, user with username: {}", userRequest.username());

        if (userRepository.existsByUsername(userRequest.username())) {
            LOG.error("<-- save, ResourceAlreadyExistsException for username: {}", userRequest.username());
            throw new ResourceAlreadyExistsException(USER, "username", userRequest.username());
        }

        final User userEntity = userMapper.toUserEntity(userRequest, passwordEncoder);
        final User savedUserEntity = userRepository.save(userEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- save, user saved with id: {}", userResponse.id());
        return userResponse;
    }

    @Transactional
    @Override
    public UserResponse update(final Long id, final UserRequest userRequest) {
        LOG.debug("--> update, user with id: {}", id);

        final User existingUserEntity = userRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- update, User with ID {} not found for update", id);
                    return new ResourceNotFoundException(USER, "id", id);
                });

        final String newName = userRequest.username();
        if (newName != null && !newName.isBlank() && !newName.equals(existingUserEntity.getUsername()) && userRepository.existsByUsername(newName)) {
            LOG.error("<-- update, failed for user with ID {}. Username '{}' already exists", id, newName);
            throw new ResourceAlreadyExistsException(USER, "username", newName);
        }

        // Partial update via updateUserEntityFromUserRequest
        final User updatedUserEntity = userMapper.updateUserEntityFromUserRequest(userRequest, existingUserEntity, passwordEncoder);
        final User savedUserEntity = userRepository.save(updatedUserEntity);
        final UserResponse userResponse = userMapper.toUserResponse(savedUserEntity);

        LOG.debug("<-- update, user updated with id: {}", userResponse.id());
        return userResponse;
    }

    @Transactional
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
        LOG.debug("--> checkLogin");
        final String username = loginRequest.username();
        final String password = Objects.requireNonNullElse(loginRequest.password(), "");

        final User user = userRepository.findByUsername(username).orElse(null);

        final String hashed = user != null ? user.getPassword() : DUMMY_HASH;
        final boolean valid = passwordEncoder.matches(password, hashed);

        if (user == null || !valid) {
            LOG.warn("<-- checkLogin, FAILED");
            throw new UnauthorizedException(USER, "credentials", "invalid");
        }

        final LoginResponse loginResponse = createLoginResponse(user);
        LOG.debug("<-- checkLogin");
        return loginResponse;
    }

    /**
     * Creates a {@link LoginResponse} containing a freshly generated JWT token with expiration metadata.
     * <p>
     * The issued-at and expiration timestamps are calculated once to ensure perfect consistency between
     * the values embedded in the JWT and those returned to the client.
     *
     * @param user the authenticated user
     * @return a {@link LoginResponse} with the JWT token, exact expiration instant and remaining seconds
     */
    private LoginResponse createLoginResponse(final User user) {
        LOG.debug("--> createLoginResponse, for username: {}", user.getUsername());
        final Instant issuedAt = Instant.now();
        final Instant expiresAt = issuedAt.plus(jwtExpirationHours, ChronoUnit.HOURS);
        final long expiresInSeconds = Duration.between(issuedAt, expiresAt).getSeconds();
        final String token = generateJwtToken(user, issuedAt, expiresAt);
        final LoginResponse loginResponse = new LoginResponse(token, expiresAt, expiresInSeconds);
        LOG.debug("<-- createLoginResponse, for username: {}", user.getUsername());
        return loginResponse;
    }

    /**
     * Generates a signed HS256 JWT for the given user using the provided timestamps.
     * <p>
     * The token contains:
     * <ul>
     *   <li>{@code iss} – configured issuer</li>
     *   <li>{@code iat} – issued-at timestamp</li>
     *   <li>{@code exp} – expiration timestamp</li>
     *   <li>{@code sub} – user ID</li>
     *   <li>{@code scope} – {@code ROLE_ADMIN} or {@code ROLE_USER}</li>
     * </ul>
     *
     * @param user      the user to issue the token for
     * @param issuedAt  exact issuance instant (must match the one used externally)
     * @param expiresAt exact expiration instant (must match the one used externally)
     * @return the compact JWT string
     */
    private String generateJwtToken(User user, Instant issuedAt, Instant expiresAt) {
        LOG.debug("--> generateJwtToken, for username: {}", user.getUsername());
        final String scope = user.isAdmin() ? Role.ADMIN.name() : Role.USER.name();

        final JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(jwtIssuer)
                .issuedAt(issuedAt)
                .expiresAt(expiresAt)
                .subject(String.valueOf(user.getId()))
                .claim("scope", scope)
                .build();

        final String token = jwtEncoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        LOG.debug("<-- generateJwtToken, for username: {}", user.getUsername());
        return token;
    }
}
