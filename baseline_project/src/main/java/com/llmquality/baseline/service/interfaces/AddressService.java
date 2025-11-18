package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import com.llmquality.baseline.entity.Address;
import org.springframework.data.domain.Pageable;


/**
 * Service interface for managing {@link Address} entities and performing
 * address-related operations for users, such as creating, updating, retrieving,
 * and deleting addresses.
 */
public interface AddressService {

    /**
     * Retrieves a paginated list of all addresses for a specific user.
     *
     * @param userId   the ID of the user whose addresses are to be fetched
     * @param pageable pagination details such as page number and size
     * @return a {@link PagedResponse} containing a list of {@link AddressResponse} objects
     */
    PagedResponse<AddressResponse> listAll(Long userId, Pageable pageable);

    /**
     * Retrieves an address by its ID for a specific user.
     *
     * @param userId    the ID of the user whose address is to be retrieved
     * @param addressId the ID of the address to retrieve
     * @return the corresponding {@link AddressResponse} for the given address ID
     */
    AddressResponse getById(Long userId, Long addressId);

    /**
     * Creates a new address for a specific user.
     *
     * @param userId         the ID of the user for whom the address is to be created
     * @param addressRequest the request object containing address details to be saved
     * @return the newly created {@link AddressResponse}
     */
    AddressResponse save(Long userId, AddressRequest addressRequest);

    /**
     * Updates an existing address for a specific user.
     *
     * @param userId         the ID of the user whose address is to be updated
     * @param addressId      the ID of the address to update
     * @param addressRequest the request object containing updated address details
     * @return the updated {@link AddressResponse}
     */
    AddressResponse update(Long userId, Long addressId, AddressRequest addressRequest);

    /**
     * Deletes an address for a specific user.
     *
     * @param userId    the ID of the user whose address is to be deleted
     * @param addressId the ID of the address to delete
     */
    void delete(Long userId, Long addressId);
}
