package com.llmquality.baseline.repository;

import com.llmquality.baseline.entity.Address;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;


@Repository
public interface AddressRepository extends JpaRepository<Address, Long> {

    Page<Address> findAllByUserId(Long userId, Pageable pageable);

    boolean existsByIdAndUserId(Long id, Long userId);
}
