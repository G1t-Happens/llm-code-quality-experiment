package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.exception.ForbiddenException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.AddressMapper;
import com.llmquality.baseline.repository.AddressRepository;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.AddressService;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.Optional;


@Service
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
                    LOG.error("<-- getById, User with ID {} not found", userId);
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
        final Address address = getAddressByIdAndUserId(addressId, userId);
        final AddressResponse addressResponse = addressMapper.toAddressResponse(address);
        LOG.debug("<-- getById, userId: {} and addressId: {}", userId, addressResponse.id());
        return addressResponse;
    }

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

    @Override
    public AddressResponse update(final Long userId, final Long addressId, final AddressRequest addressRequest) {
        LOG.debug("--> update, address with addressId: {} by userId: {}", addressId, userId);
        final Address address = getAddressByIdAndUserId(addressId, userId);

        // Partial update via updateAddressEntityFromAddressRequest
        final Address updatedAddressEntity = addressMapper.updateAddressEntityFromAddressRequest(address, addressRequest);
        final Address saveAddressEntity = addressRepository.save(updatedAddressEntity);
        final AddressResponse addressResponse = addressMapper.toAddressResponse(saveAddressEntity);
        LOG.debug("<-- update, address with addressId: {} by userId: {}", addressResponse.id(), addressResponse.userId());
        return addressResponse;
    }

    @Override
    public void delete(final Long userId, final Long addressId) {
        LOG.debug("--> delete, addressId: {}", addressId);
        final Address address = getAddressByIdAndUserId(addressId, userId);
        addressRepository.delete(address);
        LOG.debug("<-- delete, address with id {} deleted", address.getId());
    }

    /**
     * Retrieves an address by its ID and ensures that the address belongs to the specified user.
     * <p>
     * This method first checks if the address with the given ID exists. If the address is found,
     * it then verifies that the address belongs to the user identified by the provided user ID.
     * If the address does not exist, a {@link ResourceNotFoundException} is thrown.
     * If the address exists but does not belong to the specified user, a {@link ForbiddenException} is thrown.
     * </p>
     *
     * @param addressId the ID of the address to retrieve
     * @param userId    the ID of the user requesting the address
     * @return the address that belongs to the specified user
     * @throws ResourceNotFoundException if no address with the given ID exists
     * @throws ForbiddenException        if the address does not belong to the specified user
     */
    private Address getAddressByIdAndUserId(final Long addressId, final Long userId) {
        LOG.debug("--> getAddressByIdAndUserId, get address for addressId: {} and userId {}", addressId, userId);

        final Address exitingAddressEntity = addressRepository.findById(addressId)
                .orElseThrow(() -> {
                    LOG.error("<-- getAddressByIdAndUserId, Address with ID {} not found", addressId);
                    return new ResourceNotFoundException(ADDRESS, "id", addressId);
                });

        final Address permittedExitingAddressEntity = Optional.of(exitingAddressEntity)
                .filter(address -> address.getUser().getId().equals(userId))
                .orElseThrow(() -> {
                    LOG.error("<-- getAddressByIdAndUserId, User with ID {} is not authorized to access Address with ID {}", userId, addressId);
                    return new ForbiddenException(USER, "id", userId);
                });

        LOG.debug("<-- getAddressByIdAndUserId, found address for addressId: {} and userId {}",
                permittedExitingAddressEntity.getId(), permittedExitingAddressEntity.getUser().getId());
        return permittedExitingAddressEntity;
    }
}
