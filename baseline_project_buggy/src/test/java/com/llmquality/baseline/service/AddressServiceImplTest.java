package com.llmquality.baseline.service;

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
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

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
    void listAll_nullUserId_throwsNullPointerException() {
        Pageable pageable = PageRequest.of(0, 10);

        assertThrows(NullPointerException.class, () -> addressService.listAll(null, pageable));
    }

    @Test
    void getById_nullUserId_throwsNullPointerException() {
        Long addressId = 2L;

        assertThrows(NullPointerException.class, () -> addressService.getById(null, addressId));
    }

    @Test
    void save_nullUserId_throwsNullPointerException() {
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);

        assertThrows(NullPointerException.class, () -> addressService.save(null, request));
    }

}