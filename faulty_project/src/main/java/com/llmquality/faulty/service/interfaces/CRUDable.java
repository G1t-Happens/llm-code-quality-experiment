package com.llmquality.faulty.service.interfaces;

import com.llmquality.faulty.dto.PagedResponse;
import com.llmquality.faulty.exception.ResourceAlreadyExistsException;
import com.llmquality.faulty.exception.ResourceNotFoundException;
import org.springframework.data.domain.Pageable;


/**
 * Generic CRUD interface with standard type parameter naming conventions:
 * <ul>
 *     <li>R: Request / Input DTO type</li>
 *     <li>S: Response / Output DTO type</li>
 * </ul>
 *
 * @param <R> the type of the DTO used for create/update requests
 * @param <S> the type of the DTO returned in responses without sensitive data
 */
public interface CRUDable<R, S> {

    /**
     * Retrieves a paginated list of entities as response DTOs.
     *
     * <p>The result includes the content for the requested page along with
     * pagination metadata such as total elements, total pages, and whether
     * the current page is the last one.</p>
     *
     * <p>Sorting is disabled in this method; only paging parameters (page number
     * and page size) are considered.</p>
     *
     * @param pageable the pagination information (page number and page size)
     * @return a {@link PagedResponse} containing the content and pagination metadata
     */
    PagedResponse<S> listAll(Pageable pageable);

    /**
     * Retrieves an entity by its unique identifier.
     *
     * @param id the ID of the entity to retrieve
     * @return the entity represented as a response DTO
     * @throws ResourceNotFoundException if no entity with the specified ID is found
     */
    S getById(Long id) throws ResourceNotFoundException;

    /**
     * Saves a new entity from a request DTO.
     *
     * @param requestDTO the DTO containing data to create the entity
     * @return the saved entity represented as a response DTO
     * @throws ResourceAlreadyExistsException if an entity with the same unique identifier already exists
     */
    S save(R requestDTO) throws ResourceAlreadyExistsException;

    /**
     * Updates an existing entity by ID using a request DTO.
     *
     * @param id         the ID of the entity to update
     * @param requestDTO the DTO containing updated data
     * @return the updated entity represented as a response DTO
     * @throws ResourceNotFoundException if the entity with the given ID does not exist
     */
    S update(Long id, R requestDTO) throws ResourceNotFoundException;

    /**
     * Deletes an entity by its unique identifier.
     *
     * @param id the ID of the entity to delete
     * @throws ResourceNotFoundException if no entity with the specified ID exists
     */
    void delete(Long id) throws ResourceNotFoundException;
}