package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.AddressMapper;
import com.llmquality.baseline.repository.AddressRepository;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.AddressService;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Objects;


@Service
@Transactional(readOnly = true)
public class AddressServiceImpl implements AddressService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(AddressServiceImpl.class);

    private static final String USER = "User";

    private static final String ADDRESS = "Address";

    private final AddressRepository addressRepository;

    private final UserRepository userRepository;

    private final AddressMapper addressMapper;


    public AddressServiceImpl(AddressRepository addressRepository, UserRepository userRepository, AddressMapper addressMapper) {
        this.addressRepository = addressRepository;
        this.userRepository = userRepository;
        this.addressMapper = addressMapper;
    }

    @Override
    public PagedResponse<AddressResponse> listAll(final Long userId, final Pageable pageable) {
        LOG.debug("--> listAll, page={}, size={}", pageable.getPageNumber(), pageable.getPageSize());

        final User existingUserEntity = userRepository.findById(userId)
                .orElseThrow(() -> {
                    LOG.error("<-- listAll, User with ID {} not found", userId);
                    return new ResourceNotFoundException(USER, "id", userId);
                });

        final Page<AddressResponse> page = addressRepository
                .findAllByUserId(existingUserEntity.getId(), pageable)
                .map(addressMapper::toAddressResponse);
        LOG.debug("<-- listAll, total elements={}, total pages={}", page.getTotalElements(), page.getTotalPages());
        return PagedResponse.fromPage(page);
    }

    @Override
    public AddressResponse getById(Long userId, Long addressId) {
        LOG.debug("--> getById, userId: {} and addressId: {}", userId, addressId);
        final Address existingAddressEntity = addressRepository.findById(addressId)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, Address with ID {} not found", addressId);
                    return new ResourceNotFoundException(ADDRESS, "id", addressId);
                });

        enforceAddressOwnership(existingAddressEntity, userId);

        final AddressResponse addressResponse = addressMapper.toAddressResponse(existingAddressEntity);
        LOG.debug("<-- getById, userId: {} and addressId: {}", userId, addressResponse.id());
        return addressResponse;
    }

    @Transactional
    @Override
    public AddressResponse save(final Long userId, final AddressRequest addressRequest) {
        LOG.debug("--> save, address for user with userId: {}", userId);
        final User existingUserEntity = userRepository.findById(userId)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, User with userId {} not found", userId);
                    return new ResourceNotFoundException(USER, "id", userId);
                });

        final Address addressEntity = addressMapper.toAddressEntity(addressRequest, existingUserEntity);
        final AddressResponse addressResponse = addressMapper.toAddressResponse(addressRepository.save(addressEntity));
        LOG.debug("<-- save, address saved with id: {}", addressEntity.getId());
        return addressResponse;
    }

    @Transactional
    @Override
    public AddressResponse update(final Long userId, final Long addressId, final AddressRequest addressRequest) {
        LOG.debug("--> update, address with addressId: {} by userId: {}", addressId, userId);
        final Address existingAddressEntity = addressRepository.findById(addressId)
                .orElseThrow(() -> {
                    LOG.error("<-- update, Address with ID {} not found", addressId);
                    return new ResourceNotFoundException(ADDRESS, "id", addressId);
                });

        enforceAddressOwnership(existingAddressEntity, userId);

        // Partial update via updateAddressEntityFromAddressRequest
        final Address updatedAddressEntity = addressMapper.updateAddressEntityFromAddressRequest(addressRequest, existingAddressEntity);
        final Address saveAddressEntity = addressRepository.save(updatedAddressEntity);
        final AddressResponse addressResponse = addressMapper.toAddressResponse(saveAddressEntity);
        LOG.debug("<-- update, address with addressId: {} by userId: {}", addressResponse.id(), addressResponse.userId());
        return addressResponse;
    }

    @Transactional
    @Override
    public void delete(final Long userId, final Long addressId) {
        LOG.debug("--> delete, addressId: {}", addressId);
        final Address existingAddressEntity = addressRepository.findById(addressId)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, Address with ID {} not found", addressId);
                    return new ResourceNotFoundException(ADDRESS, "id", addressId);
                });

        enforceAddressOwnership(existingAddressEntity, userId);

        addressRepository.delete(existingAddressEntity);
        LOG.debug("<-- delete, address with id {} deleted", existingAddressEntity.getId());
    }

    /**
     * Enforces that the given address belongs to the requested user.
     * <p>
     * Throws {@link ResourceNotFoundException} (404) on mismatch to prevent information disclosure.
     * Must be called after loading the address and after coarse-grained {@code @PreAuthorize} check.
     * </p>
     *
     * @param address         the loaded address entity
     * @param requestedUserId the userId from the request path
     * @throws ResourceNotFoundException if address does not belong to requestedUserId
     */
    private void enforceAddressOwnership(Address address, Long requestedUserId) {
        LOG.debug("--> enforceAddressOwnership");
        final Long ownerId = (address.getUser() != null) ? address.getUser().getId() : null;

        if (!Objects.equals(ownerId, requestedUserId)) {
            LOG.warn("<-- enforceAddressOwnership, Access denied: User {} tried to access address {} (ownerId={})",
                    requestedUserId, address.getId(), ownerId);
            throw new ResourceNotFoundException(ADDRESS, "id", address.getId());
        }
        LOG.debug("<-- enforceAddressOwnership, Ownership confirmed");
    }
}
