package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import org.springframework.data.domain.Pageable;

public interface AddressService {

    PagedResponse<AddressResponse> listAll(Long userId, Pageable pageable);

    AddressResponse getById(Long userId, Long addressId);

    AddressResponse save(Long userId, AddressRequest req);

    AddressResponse update(Long userId, Long addressId, AddressRequest req);

    void delete(Long userId, Long addressId);
}