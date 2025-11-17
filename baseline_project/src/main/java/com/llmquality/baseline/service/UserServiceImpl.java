package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.user.*;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.enums.Role;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.UserMapper;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.UserService;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;


@Service
public class UserServiceImpl implements UserService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(UserServiceImpl.class);

    private static final String USER = "User";

    private final UserRepository userRepository;

    private final PasswordEncoder passwordEncoder;

    private final JwtEncoder jwtEncoder;

    private final UserMapper userMapper;

    @Value("${jwt.issuer:self}")
    private String jwtIssuer;

    @Value("${jwt.expiration:1}")
    private long jwtExpirationHours;


    @Autowired
    public UserServiceImpl(final UserRepository userRepository, final PasswordEncoder passwordEncoder, final JwtEncoder jwtEncoder, final UserMapper userMapper) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtEncoder = jwtEncoder;
        this.userMapper = userMapper;
    }

    @Override
    public PagedResponse<UserResponse> listAll(final Pageable pageable) {
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

    @Override
    public UserResponse save(final UserRequest userRequest) {
        LOG.debug("--> save, user with name: {}", userRequest.getUsername());

        if (userRepository.existsByUsername(userRequest.getUsername())) {
            LOG.error("<-- save, ResourceAlreadyExistsException for name: {}", userRequest.getUsername());
            throw new ResourceAlreadyExistsException(USER, "name", userRequest.getUsername());
        }

        final User userEntity = userMapper.toUserEntity(userRequest, passwordEncoder);
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

        final String newName = userRequest.getUsername();
        if (newName != null && !newName.equals(existingUserEntity.getUsername()) && userRepository.existsByUsername(newName)) {
            LOG.error("<-- update, failed for user with ID {}. Username '{}' already exists", id, newName);
            throw new ResourceAlreadyExistsException(USER, "name", newName);
        }

        // Partial update via updateUserEntityFromUserRequest
        final User updateUserEntity = userMapper.updateUserEntityFromUserRequest(userRequest, existingUserEntity, passwordEncoder);
        final User savedUserEntity = userRepository.save(updateUserEntity);
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

        userRepository.delete(existingUserEntity);
        LOG.debug("<-- delete, user with id {} deleted", existingUserEntity.getId());
    }

    @Override
    public LoginResponse checkLogin(final LoginRequest loginRequest) {
        LOG.debug("--> checkLogin, username: {}", loginRequest.getUsername());

        final User user = userRepository.findByUsername(loginRequest.getUsername())
                .orElseThrow(() -> {
                    LOG.error("<-- checkLogin, user '{}' not found", loginRequest.getUsername());
                    return new ResourceNotFoundException("User", "username", loginRequest.getUsername());
                });

        if (!passwordEncoder.matches(loginRequest.getPassword(), user.getPassword())) {
            LOG.warn("<-- checkLogin, bad credentials for '{}'", loginRequest.getUsername());
            return new LoginResponse(false, null);
        }

        final List<GrantedAuthority> authorities = mapAuthorities(user);
        final Authentication authentication = createAuthentication(user.getUsername(), authorities);
        final String token = generateJwt(authentication);

        LOG.debug("<-- checkLogin, login successful for '{}'", loginRequest.getUsername());
        return new LoginResponse(true, token);
    }

    /**
     * Maps the user's role to a list of granted authorities for Spring Security.
     *
     * @param user the user whose roles are to be mapped
     * @return list of granted authorities
     */
    private List<GrantedAuthority> mapAuthorities(User user) {
        LOG.debug("--> mapAuthorities, for user: {}", user.getId());
        List<GrantedAuthority> grantedAuthorities = user.isAdmin()
                ? List.of(new SimpleGrantedAuthority(Role.ADMIN.getName()))
                : List.of(new SimpleGrantedAuthority(Role.USER.getName()));
        LOG.debug("<-- mapAuthorities, for user: {}", user.getId());
        return grantedAuthorities;
    }

    /**
     * Creates an Authentication object for a given username and authorities.
     *
     * @param username    the username of the authenticated user
     * @param authorities the granted authorities for the user
     * @return an Authentication token
     */
    private Authentication createAuthentication(String username, List<GrantedAuthority> authorities) {
        LOG.debug("--> createAuthentication, user={}", username);
        Authentication auth = new UsernamePasswordAuthenticationToken(username, null, authorities);
        LOG.debug("<-- createAuthentication, user={}", username);
        return auth;
    }

    /**
     * Generates a JWT token for a given authentication object.
     *
     * @param authentication the authentication containing user details and roles
     * @return a signed JWT token as String
     */
    private String generateJwt(Authentication authentication) {
        LOG.debug("--> generateJwt, username: {}", authentication.getName());
        final Instant now = Instant.now();
        final List<String> roles = extractRoles(authentication);

        final JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(jwtIssuer)
                .issuedAt(now)
                .expiresAt(now.plus(jwtExpirationHours, ChronoUnit.HOURS))
                .subject(authentication.getName())
                .claim("roles", roles)
                .build();

        final String jwt = jwtEncoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        LOG.debug("<-- generateJwt, username: {}", authentication.getName());
        return jwt;
    }

    /**
     * Extracts role names from the granted authorities in an authentication object.
     *
     * @param authentication the authentication containing granted authorities
     * @return list of role names
     */
    private List<String> extractRoles(Authentication authentication) {
        LOG.debug("--> extractRoles");
        final List<String> roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();
        LOG.debug("<-- extractRoles, {} roles extracted", roles.size());
        return roles;
    }
}
