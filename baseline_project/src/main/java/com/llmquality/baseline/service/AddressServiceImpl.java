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
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

@Service
public class AddressServiceImpl implements AddressService {

    private final AddressRepository addressRepo;
    private final UserRepository userRepo;
    private final AddressMapper mapper;

    public AddressServiceImpl(AddressRepository addressRepo, UserRepository userRepo, AddressMapper mapper) {
        this.addressRepo = addressRepo;
        this.userRepo = userRepo;
        this.mapper = mapper;
    }

    @Override
    public PagedResponse<AddressResponse> listAll(Long userId, Pageable pageable) {
        userRepo.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", userId));

        Page<Address> page = addressRepo.findAllByUserId(userId, pageable);
        return PagedResponse.fromPage(page.map(mapper::toAddressResponse));
    }

    @Override
    public AddressResponse getById(Long userId, Long addressId) {
        Address address = getAddressByIdAndUserId(addressId, userId);
        return mapper.toAddressResponse(address);
    }

    @Override
    public AddressResponse save(Long userId, AddressRequest req) {
        User user = userRepo.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", userId));

        Address address = mapper.toAddressEntity(req, user);
        return mapper.toAddressResponse(addressRepo.save(address));
    }

    @Override
    public AddressResponse update(Long userId, Long addressId, AddressRequest req) {
        Address address = getAddressByIdAndUserId(addressId, userId);
        mapper.updateAddressEntityFromAddressRequest(address, req);
        return mapper.toAddressResponse(addressRepo.save(address));
    }

    @Override
    public void delete(Long userId, Long addressId) {
        Address address = getAddressByIdAndUserId(addressId, userId);
        addressRepo.delete(address);
    }

    private Address getAddressByIdAndUserId(Long addressId, Long userId) {
        return addressRepo.findById(addressId)
                .filter(a -> a.getUser().getId().equals(userId))
                .orElseThrow(() -> new ResourceNotFoundException("Address", "id", addressId));
    }
}