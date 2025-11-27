package com.llmquality.baseline.llmgenerated.service;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.enums.AddressType;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.AddressMapper;
import com.llmquality.baseline.repository.AddressRepository;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.AddressServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AddressServiceImplTest {

    @Mock
    private AddressRepository addressRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private AddressMapper addressMapper;

    @InjectMocks
    private AddressServiceImpl addressService;

    @Test
    void listAll_userExists_returnsPagedResponse() {
        Long userId = 1L;
        User user = new User();
        user.setId(userId);
        Pageable pageable = PageRequest.of(0, 10);
        Page<Address> addressPage = new PageImpl<>(List.of(new Address()), pageable, 1L);
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));
        when(addressRepository.findAllByUserId(userId, pageable)).thenReturn(addressPage);

        PagedResponse<AddressResponse> result = addressService.listAll(userId, pageable);

        assertNotNull(result);
        assertEquals(0, result.page());
        verify(addressRepository).findAllByUserId(userId, pageable);
    }

    @Test
    void listAll_userNotFound_throwsResourceNotFoundException() {
        Long userId = 999L;
        Pageable pageable = PageRequest.of(0, 10);
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> addressService.listAll(userId, pageable));
    }

    @Test
    void listAll_nullUserId_throwsNullPointerException() {
        Pageable pageable = PageRequest.of(0, 10);

        assertThrows(NullPointerException.class, () -> addressService.listAll(null, pageable));
    }

    @Test
    void getById_addressExistsAndOwned_returnsAddressResponse() {
        Long userId = 1L;
        Long addressId = 2L;
        Address address = new Address();
        address.setId(addressId);
        User owner = new User();
        owner.setId(userId);
        address.setUser(owner);
        AddressResponse expected = new AddressResponse(addressId, "street", "10", "12345", "city", "country", AddressType.PRIVATE, userId);
        when(addressRepository.findById(addressId)).thenReturn(Optional.of(address));
        when(addressMapper.toAddressResponse(address)).thenReturn(expected);

        AddressResponse result = addressService.getById(userId, addressId);

        assertEquals(expected, result);
        verify(addressMapper).toAddressResponse(address);
    }

    @Test
    void getById_addressNotFound_throwsResourceNotFoundException() {
        Long userId = 1L;
        Long addressId = 999L;
        when(addressRepository.findById(addressId)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> addressService.getById(userId, addressId));
    }

    @Test
    void getById_addressNotOwned_throwsResourceNotFoundException() {
        Long userId = 1L;
        Long addressId = 2L;
        Address address = new Address();
        address.setId(addressId);
        User owner = new User();
        owner.setId(999L);
        address.setUser(owner);
        when(addressRepository.findById(addressId)).thenReturn(Optional.of(address));

        assertThrows(ResourceNotFoundException.class, () -> addressService.getById(userId, addressId));
    }

    @Test
    void getById_nullUserId_throwsNullPointerException() {
        Long addressId = 2L;

        assertThrows(NullPointerException.class, () -> addressService.getById(null, addressId));
    }

    @Test
    void getById_nullAddressId_throwsIllegalArgumentException() {
        Long userId = 1L;

        assertThrows(IllegalArgumentException.class, () -> addressService.getById(userId, null));
    }

    @Test
    void save_userExists_persistsAndReturnsAddressResponse() {
        Long userId = 1L;
        User user = new User();
        user.setId(userId);
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);
        Address addressEntity = new Address();
        addressEntity.setId(2L);
        AddressResponse expectedResponse = new AddressResponse(2L, "street", "10", "12345", "city", "country", AddressType.PRIVATE, userId);
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));
        when(addressMapper.toAddressEntity(request, user)).thenReturn(addressEntity);
        when(addressMapper.toAddressResponse(addressEntity)).thenReturn(expectedResponse);

        AddressResponse result = addressService.save(userId, request);

        assertEquals(expectedResponse, result);
        verify(addressRepository).save(addressEntity); // Fails: exposes bug, save never called in prod
    }

    @Test
    void save_userNotFound_throwsResourceNotFoundException() {
        Long userId = 999L;
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);
        when(userRepository.findById(userId)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> addressService.save(userId, request));
    }

    @Test
    void save_nullUserId_throwsNullPointerException() {
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);

        assertThrows(NullPointerException.class, () -> addressService.save(null, request));
    }

    @Test
    void save_nullRequest_throwsNullPointerException() {
        Long userId = 1L;

        assertThrows(NullPointerException.class, () -> addressService.save(userId, null));
    }

    @Test
    void update_addressExists_persistsAndReturnsUpdatedResponse() {
        Long userId = 1L;
        Long addressId = 2L;
        AddressRequest request = new AddressRequest("new street", "20", "54321", "new city", "new country", AddressType.BUSINESS);
        Address existingAddress = new Address();
        existingAddress.setId(addressId);
        User owner = new User();
        owner.setId(userId);
        existingAddress.setUser(owner);
        Address savedAddress = new Address();
        savedAddress.setId(addressId);
        AddressResponse expected = new AddressResponse(addressId, "new street", "20", "54321", "new city", "new country", AddressType.BUSINESS, userId);
        when(addressRepository.findById(addressId)).thenReturn(Optional.of(existingAddress));
        when(addressMapper.updateAddressEntityFromAddressRequest(request, existingAddress)).thenReturn(savedAddress);
        when(addressRepository.save(savedAddress)).thenReturn(savedAddress);
        when(addressMapper.toAddressResponse(savedAddress)).thenReturn(expected);

        AddressResponse result = addressService.update(userId, addressId, request);

        assertEquals(expected, result);
        verify(addressRepository).save(savedAddress);
    }

    @Test
    void update_addressNotFound_throwsResourceNotFoundException() {
        Long userId = 1L;
        Long addressId = 999L;
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);
        when(addressRepository.findById(addressId)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> addressService.update(userId, addressId, request));
    }

    @Test
    void delete_addressExists_deletesAddress() {
        Long userId = 1L;
        Long addressId = 2L;
        Address address = new Address();
        address.setId(addressId);
        User owner = new User();
        owner.setId(userId);
        address.setUser(owner);
        when(addressRepository.findById(addressId)).thenReturn(Optional.of(address));

        addressService.delete(userId, addressId);

        verify(addressRepository).delete(address);
    }

    @Test
    void delete_addressNotFound_throwsResourceNotFoundException() {
        Long userId = 1L;
        Long addressId = 999L;
        when(addressRepository.findById(addressId)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> addressService.delete(userId, addressId));
    }
}